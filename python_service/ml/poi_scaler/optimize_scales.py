import pandas as pd
import numpy as np
import torch
import torch.optim as optim
from etl.common.db import get_conn
from sklearn.model_selection import train_test_split
from ml.poi_scaler.poi_scale_optimizer import POIScaleOptimizer, prepare_pytorch_tensors 

BASE_SCALE = 800.0
POI_MAX_RADII = torch.tensor(
    [4000, 5000, 10000, 5000, 3000, 10000, 6000, 6000, 5000, 8000, 5000, 5000],
    dtype=torch.float32
)
POI_PRIOR_SCALES = POI_MAX_RADII * 0.6
MIN_SCALE = 200.0

POI_COLS = [
    'school_distances',
    'kindergarten_distances',
    'train_station_distances',
    'light_rail_stop_distances',
    'bus_stop_distances',
    'hospital_distances',
    'clinic_distances',
    'park_distances',
    'supermarket_distances',
    'mall_distances',
    'commercial_distances',
    'hotel_distances'
]

def fetch_raw_distances():
    """Step 1: Get the raw distance arrays from PostgreSQL"""
    print("Fetching raw distances from database...")
    conn = get_conn()
    
    query = """
        WITH sampled_properties AS (
            SELECT s.property_id, s.log_change, s.snapshot_year, p.geom
            FROM property_features_snapshot s
            JOIN properties p ON s.property_id = p.property_id
            WHERE s.horizon_years = 5 
            AND s.log_change IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 7000
        ),
        poi_with_distances AS (
            SELECT 
                sp.property_id,
                pc.poi_type_id,
                ST_Distance(sp.geom::geography, pc.geom::geography) AS distance
            FROM sampled_properties sp
            JOIN poi_current pc ON ST_DWithin(sp.geom, pc.geom, 0.1)
            WHERE (pc.opening_year IS NULL OR pc.opening_year <= sp.snapshot_year)
            AND (
                (pc.poi_type_id = 1 AND ST_DWithin(sp.geom::geography, pc.geom::geography, 4000))
                OR (pc.poi_type_id = 2 AND ST_DWithin(sp.geom::geography, pc.geom::geography, 5000))
                OR (pc.poi_type_id = 3 AND ST_DWithin(sp.geom::geography, pc.geom::geography, 10000))
                OR (pc.poi_type_id = 4 AND ST_DWithin(sp.geom::geography, pc.geom::geography, 5000))
                OR (pc.poi_type_id = 5 AND ST_DWithin(sp.geom::geography, pc.geom::geography, 3000))
                OR (pc.poi_type_id = 6 AND ST_DWithin(sp.geom::geography, pc.geom::geography, 10000))
                OR (pc.poi_type_id = 7 AND ST_DWithin(sp.geom::geography, pc.geom::geography, 6000))
                OR (pc.poi_type_id = 8 AND ST_DWithin(sp.geom::geography, pc.geom::geography, 6000))
                OR (pc.poi_type_id = 9 AND ST_DWithin(sp.geom::geography, pc.geom::geography, 5000))
                OR (pc.poi_type_id = 10 AND ST_DWithin(sp.geom::geography, pc.geom::geography, 8000))
                OR (pc.poi_type_id = 11 AND ST_DWithin(sp.geom::geography, pc.geom::geography, 5000))
                OR (pc.poi_type_id = 12 AND ST_DWithin(sp.geom::geography, pc.geom::geography, 5000))
            )
        )
        SELECT 
            sp.property_id,
            sp.log_change,
            ARRAY_AGG(pd.distance ORDER BY pd.distance) FILTER (WHERE pd.poi_type_id = 1) AS school_distances,
            ARRAY_AGG(pd.distance ORDER BY pd.distance) FILTER (WHERE pd.poi_type_id = 2) AS kindergarten_distances,
            ARRAY_AGG(pd.distance ORDER BY pd.distance) FILTER (WHERE pd.poi_type_id = 3) AS train_station_distances,
            ARRAY_AGG(pd.distance ORDER BY pd.distance) FILTER (WHERE pd.poi_type_id = 4) AS light_rail_stop_distances,
            ARRAY_AGG(pd.distance ORDER BY pd.distance) FILTER (WHERE pd.poi_type_id = 5) AS bus_stop_distances,
            ARRAY_AGG(pd.distance ORDER BY pd.distance) FILTER (WHERE pd.poi_type_id = 6) AS hospital_distances,
            ARRAY_AGG(pd.distance ORDER BY pd.distance) FILTER (WHERE pd.poi_type_id = 7) AS clinic_distances,
            ARRAY_AGG(pd.distance ORDER BY pd.distance) FILTER (WHERE pd.poi_type_id = 8) AS park_distances,
            ARRAY_AGG(pd.distance ORDER BY pd.distance) FILTER (WHERE pd.poi_type_id = 9) AS supermarket_distances,
            ARRAY_AGG(pd.distance ORDER BY pd.distance) FILTER (WHERE pd.poi_type_id = 10) AS mall_distances,
            ARRAY_AGG(pd.distance ORDER BY pd.distance) FILTER (WHERE pd.poi_type_id = 11) AS commercial_distances,
            ARRAY_AGG(pd.distance ORDER BY pd.distance) FILTER (WHERE pd.poi_type_id = 12) AS hotel_distances
        FROM sampled_properties sp
        LEFT JOIN poi_with_distances pd ON sp.property_id = pd.property_id
        GROUP BY sp.property_id, sp.log_change;
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def run_optimization(df, reg_lambda=0.0, seed=42, max_epochs=250, patience=30):
    torch.manual_seed(seed)
    np.random.seed(seed)

    df_train, df_val = train_test_split(df, test_size=0.2, random_state=seed)
    X_train, mask_train, y_train = prepare_pytorch_tensors(df_train, POI_COLS)
    X_val, mask_val, y_val = prepare_pytorch_tensors(df_val, POI_COLS)

    model = POIScaleOptimizer(num_poi_types=len(POI_COLS))
    with torch.no_grad():
        # prior-centered init + tiny seed-dependent jitter
        model.scale_logs.copy_(torch.log(POI_PRIOR_SCALES / BASE_SCALE) + 0.01 * torch.randn_like(POI_PRIOR_SCALES))

    optimizer = optim.Adam(model.parameters(), lr=0.01, weight_decay=1e-4)
    criterion = torch.nn.HuberLoss(delta=1.0)

    min_log = torch.log(torch.tensor(MIN_SCALE / BASE_SCALE))
    max_log = torch.log(POI_MAX_RADII / BASE_SCALE)

    best_val, best_state = float("inf"), None
    no_improve = 0

    for epoch in range(max_epochs):
        model.train()
        optimizer.zero_grad()
        predictions = model(X_train, mask_train)
        data_loss = criterion(predictions, y_train)

        current_scales = torch.exp(model.scale_logs) * BASE_SCALE
        prior_penalty = torch.mean((torch.log(current_scales) - torch.log(POI_PRIOR_SCALES)) ** 2)
        train_loss = data_loss + reg_lambda * prior_penalty
        train_loss.backward()
        optimizer.step()

        with torch.no_grad():
            model.scale_logs.data = torch.max(model.scale_logs.data, min_log)
            model.scale_logs.data = torch.min(model.scale_logs.data, max_log)

        if epoch % 10 == 0:
            model.eval()
            with torch.no_grad():
                val_preds = model(X_val, mask_val)
                val_data_loss = criterion(val_preds, y_val)
                val_scales = torch.exp(model.scale_logs) * BASE_SCALE
                val_prior_penalty = torch.mean((torch.log(val_scales) - torch.log(POI_PRIOR_SCALES)) ** 2)
                val_loss = val_data_loss + reg_lambda * val_prior_penalty

            print(f"[seed={seed}] Epoch {epoch} | Train {train_loss.item():.4f} | Val {val_loss.item():.4f}")

            if val_loss.item() < best_val:
                best_val = val_loss.item()
                best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
                no_improve = 0
            else:
                no_improve += 1
                if no_improve >= patience:
                    break

    if best_state is not None:
        model.load_state_dict(best_state)

    final_scales = (torch.exp(model.scale_logs) * BASE_SCALE).detach().cpu().numpy()

    print("\n" + "=" * 50)
    print(f"OPTIMAL SCALES FOUND (seed={seed}, lambda={reg_lambda})")
    print("=" * 50)
    for name, scale in zip(POI_COLS, final_scales):
        print(f"{name}: {scale:.1f} meters")

    return {"seed": seed, "best_val": best_val, "scales": final_scales}


if __name__ == "__main__":
    df_once = fetch_raw_distances()

    seeds = [11, 42, 77]
    results = [run_optimization(df_once, reg_lambda=0.0, seed=s) for s in seeds]

    all_scales = np.stack([r["scales"] for r in results], axis=0)
    mean_scales = all_scales.mean(axis=0)
    std_scales = all_scales.std(axis=0)
    best_run = min(results, key=lambda r: r["best_val"])

    print("\n" + "=" * 50)
    print("SEED SUMMARY")
    print("=" * 50)
    print(f"Best seed: {best_run['seed']} | Best Val Loss: {best_run['best_val']:.4f}")
    for name, m, s in zip(POI_COLS, mean_scales, std_scales):
        print(f"{name}: mean={m:.1f}m | std={s:.1f}m")
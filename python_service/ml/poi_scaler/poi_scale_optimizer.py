import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F

class POIScaleOptimizer(nn.Module):
    def __init__(self, num_poi_types):
        super().__init__()
        self.scale_logs = nn.Parameter(torch.zeros(num_poi_types))
        self.register_buffer('weights', torch.ones(num_poi_types))
        self.bias = nn.Parameter(torch.zeros(1))

    def forward(self, distance_arrays, masks):
        scales = torch.exp(self.scale_logs) * 800.0
        scales = scales.view(1, -1, 1)
        w = self.weights.view(1, -1)

        decay_scores = torch.exp(-distance_arrays / scales) * masks

        # use mean instead of sum to reduce POI-count bias
        counts = masks.sum(dim=2).clamp_min(1.0)
        mean_scores = decay_scores.sum(dim=2) / counts

        final_prediction = torch.sum(w * mean_scores, dim=1) + self.bias
        return final_prediction


def prepare_pytorch_tensors(df, poi_columns, max_pois_per_type=20):
    """Converts a dataframe of distance lists into padded PyTorch tensors."""
    num_samples = len(df)
    num_poi_types = len(poi_columns)
    
    distances_matrix = torch.zeros((num_samples, num_poi_types, max_pois_per_type))
    masks_matrix = torch.zeros((num_samples, num_poi_types, max_pois_per_type))
    
    for i, (original_idx, row) in enumerate(df.iterrows()):
        for type_idx, col_name in enumerate(poi_columns):
            dist_list = row[col_name]
            
            # If the database returned None (no POIs found), skip it
            if dist_list is None or len(dist_list) == 0:
                continue
                
            dist_list = sorted(dist_list)[:max_pois_per_type]
            count = len(dist_list)
            
            # FIX: We now insert into slot `i` instead of the pandas index
            distances_matrix[i, type_idx, :count] = torch.tensor(dist_list)
            masks_matrix[i, type_idx, :count] = 1.0 
            
    targets = torch.tensor(df['log_change'].values, dtype=torch.float32)
    return distances_matrix, masks_matrix, targets

from etl.common.db import get_conn

def main():
    horizons = [5, 10]         # add 7 if you want
    start_year = 1998
    end_year = 2024
    eps = 0.01

    with get_conn() as conn:
        with conn.cursor() as cur:
            for h in horizons:
                last_snapshot = end_year - h
                for y in range(start_year, last_snapshot + 1):
                    print(f"Building snapshot year={y} horizon={h}")
                    cur.execute("SELECT public.build_property_snapshot(%s::int, %s::smallint, %s::double precision);", (y, h, eps))
                    conn.commit()

if __name__ == "__main__":
    main()
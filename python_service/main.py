from poi.enrichment import enrich_poi

if __name__ == "__main__":
    print("hello world")

    test_pois = [
        ("Kiryat Motzkin Railway Station","תחנת קיריית מוצקין", "train_station", 32.833, 35.07),
        ("Tel Aviv Savidor Center","תל אביב סבידור מרכז", "train_station", 32.092, 34.789),
        ("Sheba Medical Center","בית חולים שיבא", "hospital", 32.045, 34.845),
        ("Azrieli Mall Tel Aviv","קניון עזריאלי", "mall", 32.074, 34.792),
        ("Technion – Israel Institute of Technology","טכניון", "university", 32.777, 35.021),
        ("NAME", "NAME", "TYPE", 34.23, 35.021),
    ]

    for name,name_he, poi_type, lat, lon in test_pois:
        result = enrich_poi(name, name_he, poi_type, lat, lon)
        #result = get_poi_opening_year_cached(name, poi_type, lat, lon)
        print(f"{poi_type.upper():15} | {name:40} → {result}")

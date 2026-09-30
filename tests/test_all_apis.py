import httpx
import asyncio
import json

async def test_all_apis():
    results = {}
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1. SkyTruth Cerulean API (Oil Slicks)
        print("=" * 60)
        print("1. SKYTRUTH CERULEAN API (Oil Slick Data)")
        print("=" * 60)
        try:
            url = "https://api.cerulean.skytruth.org/collections/public.slick_plus/items?f=json&limit=5"
            r = await client.get(url)
            print(f"   Status: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                features = data.get("features", [])
                print(f"   Features count: {len(features)}")
                if features:
                    print(f"   First feature keys: {list(features[0].keys())}")
                    print(f"   First feature props: {json.dumps(features[0].get('properties', {}), indent=4)[:500]}")
                results["skytruth"] = "OK" if features else "EMPTY"
            else:
                print(f"   Response: {r.text[:300]}")
                results["skytruth"] = f"HTTP {r.status_code}"
        except Exception as e:
            print(f"   ERROR: {e}")
            results["skytruth"] = f"FAIL: {e}"

        # 2. Digitraffic AIS Locations (Live Vessel Positions)
        print("\n" + "=" * 60)
        print("2. DIGITRAFFIC AIS LOCATIONS (Live Vessels)")
        print("=" * 60)
        try:
            url = "https://meri.digitraffic.fi/api/ais/v1/locations"
            headers = {"Accept-Encoding": "gzip", "Digitraffic-User": "OceanPulse/1.0"}
            r = await client.get(url, headers=headers)
            print(f"   Status: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                features = data.get("features", [])
                print(f"   Total vessels: {len(features)}")
                if features:
                    sample = features[0]
                    props = sample.get("properties", {})
                    geom = sample.get("geometry", {})
                    print(f"   Sample MMSI: {props.get('mmsi')}")
                    print(f"   Sample SOG: {props.get('sog')}")
                    print(f"   Sample coords: {geom.get('coordinates')}")
                    # Count vessels with sog >= 2
                    moving = [f for f in features if f.get("properties", {}).get("sog", 0) >= 2.0]
                    print(f"   Moving vessels (sog>=2): {len(moving)}")
                    # Check lat/lon ranges
                    lats = [f.get("geometry", {}).get("coordinates", [0, 0])[1] for f in moving[:100]]
                    lons = [f.get("geometry", {}).get("coordinates", [0, 0])[0] for f in moving[:100]]
                    if lats:
                        print(f"   Lat range: {min(lats):.2f} to {max(lats):.2f}")
                        print(f"   Lon range: {min(lons):.2f} to {max(lons):.2f}")
                results["digitraffic_locations"] = "OK" if features else "EMPTY"
            else:
                print(f"   Response: {r.text[:300]}")
                results["digitraffic_locations"] = f"HTTP {r.status_code}"
        except Exception as e:
            print(f"   ERROR: {e}")
            results["digitraffic_locations"] = f"FAIL: {e}"

        # 3. Digitraffic AIS Vessels (Metadata)
        print("\n" + "=" * 60)
        print("3. DIGITRAFFIC AIS VESSELS (Vessel Metadata)")
        print("=" * 60)
        try:
            url = "https://meri.digitraffic.fi/api/ais/v1/vessels"
            headers = {"Accept-Encoding": "gzip", "Digitraffic-User": "OceanPulse/1.0"}
            r = await client.get(url, headers=headers)
            print(f"   Status: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                print(f"   Vessels count: {len(data) if isinstance(data, list) else 'N/A (dict)'}")
                if isinstance(data, list) and data:
                    print(f"   Sample vessel: {json.dumps(data[0], indent=4)[:400]}")
                results["digitraffic_vessels"] = "OK"
            else:
                print(f"   Response: {r.text[:300]}")
                results["digitraffic_vessels"] = f"HTTP {r.status_code}"
        except Exception as e:
            print(f"   ERROR: {e}")
            results["digitraffic_vessels"] = f"FAIL: {e}"

        # 4. Open-Meteo Wind API
        print("\n" + "=" * 60)
        print("4. OPEN-METEO WIND API (Weather)")
        print("=" * 60)
        try:
            url = "https://api.open-meteo.com/v1/forecast?latitude=18.95&longitude=72.25&current=wind_speed_10m,wind_direction_10m&wind_speed_unit=kn"
            r = await client.get(url)
            print(f"   Status: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                current = data.get("current", {})
                print(f"   Wind speed: {current.get('wind_speed_10m')} knots")
                print(f"   Wind direction: {current.get('wind_direction_10m')}°")
                results["open_meteo_wind"] = "OK"
            else:
                print(f"   Response: {r.text[:300]}")
                results["open_meteo_wind"] = f"HTTP {r.status_code}"
        except Exception as e:
            print(f"   ERROR: {e}")
            results["open_meteo_wind"] = f"FAIL: {e}"

        # 5. Open-Meteo Marine API
        print("\n" + "=" * 60)
        print("5. OPEN-METEO MARINE API (Ocean Currents)")
        print("=" * 60)
        try:
            url = "https://marine-api.open-meteo.com/v1/marine?latitude=18.95&longitude=72.25&current=wave_height,ocean_current_velocity,ocean_current_direction"
            r = await client.get(url)
            print(f"   Status: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                current = data.get("current", {})
                print(f"   Wave height: {current.get('wave_height')}")
                print(f"   Current velocity: {current.get('ocean_current_velocity')}")
                print(f"   Current direction: {current.get('ocean_current_direction')}")
                results["open_meteo_marine"] = "OK"
            else:
                print(f"   Response: {r.text[:300]}")
                results["open_meteo_marine"] = f"HTTP {r.status_code}"
        except Exception as e:
            print(f"   ERROR: {e}")
            results["open_meteo_marine"] = f"FAIL: {e}"

        # 6. Copernicus Sentinel API (SAR passes)
        print("\n" + "=" * 60)
        print("6. COPERNICUS SENTINEL API (SAR Passes)")
        print("=" * 60)
        try:
            polygon = "71.0 18.0, 72.7 18.0, 72.7 19.8, 71.0 19.8, 71.0 18.0"
            url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'SENTINEL-1' and OData.CSC.Intersects(area=geography'SRID=4326;POLYGON(({polygon}))')&$orderby=ContentDate/Start desc&$top=3"
            r = await client.get(url)
            print(f"   Status: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                values = data.get("value", [])
                print(f"   SAR passes found: {len(values)}")
                if values:
                    print(f"   Latest: {values[0].get('Name')} at {values[0].get('ContentDate', {}).get('Start')}")
                results["copernicus"] = "OK" if values else "EMPTY"
            else:
                print(f"   Response: {r.text[:300]}")
                results["copernicus"] = f"HTTP {r.status_code}"
        except Exception as e:
            print(f"   ERROR: {e}")
            results["copernicus"] = f"FAIL: {e}"

        # 7. Test is_strictly_ocean filter
        print("\n" + "=" * 60)
        print("7. GEO FILTER TEST (is_strictly_ocean)")
        print("=" * 60)
        from global_land_mask import globe
        test_points = [
            (18.93, 72.50, "Mumbai offshore"),
            (59.5, 24.5, "Gulf of Finland"),
            (60.0, 25.0, "Helsinki coast"),
            (60.7, 24.0, "Blocked by filter (lat>60.55, lon>23.8)"),
            (57.5, 20.0, "Baltic Sea open"),
            (55.0, 13.0, "Danish Straits"),
        ]
        for lat, lon, desc in test_points:
            is_ocean = bool(globe.is_ocean(lat, lon))
            blocked_by_filter = lat > 60.55 and lon > 23.8
            print(f"   {desc}: ocean={is_ocean}, blocked_by_inland_filter={blocked_by_filter}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for k, v in results.items():
        status = "[OK]" if v == "OK" else "[FAIL]"
        print(f"   {status} {k}: {v}")

if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(test_all_apis())

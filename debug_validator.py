from api.kite_client import create_client
from datetime import datetime

client = create_client()

# Add exception handling to see full traceback
try:
    result = client.fetch_and_save(
        exchange='NSE',
        symbol='RELIANCE',
        instrument_token=738561,
        from_date=datetime(2023, 1, 1),
        to_date=datetime(2024, 1, 1),
        interval='day',
        validate=True,
        overwrite=False
    )
    print(result)
except Exception as e:
    import traceback
    print("Full error traceback:")
    traceback.print_exc()
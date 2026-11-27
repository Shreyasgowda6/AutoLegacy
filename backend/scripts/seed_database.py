"""Run from backend/: python -m scripts.seed_database (requires an API key)."""
from app.config import load_settings
from app.dependencies import build_services


def main():
    services = build_services(load_settings())
    records = services.demo_storage.all()
    for record in records:
        if record.source_type != 'synthetic' or record.verification_status != 'unverified':
            raise ValueError('Demo dataset must contain only unverified synthetic records')
        services.index.upsert(record)
    print(f'Indexed {len(records)} explicitly synthetic records in the separate demo collection.')


if __name__ == '__main__':
    main()

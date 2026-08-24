import json
import logging
import os
from datetime import datetime, date, timedelta
from decimal import Decimal

import requests

from core.models import MarketPrice

logger = logging.getLogger(__name__)


class PriceEngine:
    def __init__(self, api_key: str | None = None, cache_dir: str = 'data'):
        self.api_key = api_key
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(self.cache_dir, 'price_cache.json')
        os.makedirs(self.cache_dir, exist_ok=True)

    def fetch_live_prices(self, commodity: str, state: str = 'Tamil Nadu') -> list[MarketPrice]:
        if not self.api_key:
            logger.warning("No API key provided, falling back to cache.")
            return self._load_fallback(commodity)

        url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
        params = {
            'api-key': self.api_key,
            'format': 'json',
            'filters[commodity]': commodity,
            'filters[state]': state,
            'limit': 50
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'records' not in data or not data['records']:
                logger.info(f"No live records found for {commodity} in {state}.")
                return self._load_fallback(commodity)
                
            prices = []
            for record in data['records']:
                try:
                    price = MarketPrice(
                        market_name=record.get('market', 'Unknown'),
                        commodity=record.get('commodity', commodity),
                        variety=record.get('variety', 'Unknown'),
                        min_price=Decimal(str(record.get('min_price', 0))),
                        max_price=Decimal(str(record.get('max_price', 0))),
                        modal_price=Decimal(str(record.get('modal_price', 0))),
                        unit="Quintal",
                        arrival_date=datetime.strptime(record.get('arrival_date', date.today().strftime("%d/%m/%Y")), "%d/%m/%Y").date(),
                        state=record.get('state', state),
                        district=record.get('district', 'Unknown'),
                        source='api',
                        fetched_at=datetime.now()
                    )
                    prices.append(price)
                except Exception as e:
                    logger.error(f"Error parsing record: {e}")
                    
            if prices:
                self._update_cache(prices)
            else:
                return self._load_fallback(commodity)
                
            return prices

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return self._load_fallback(commodity)
        except Exception as e:
            logger.error(f"Unexpected error in fetch_live_prices: {e}")
            return self._load_fallback(commodity)

    def _load_fallback(self, commodity: str) -> list[MarketPrice]:
        if not os.path.exists(self.cache_file):
            logger.warning("Fallback cache file not found.")
            return []
            
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            prices = []
            for item in data:
                if item.get('commodity', '').lower() == commodity.lower():
                    item['source'] = 'fallback'
                    item['fetched_at'] = datetime.now()
                    prices.append(MarketPrice(**item))
            return prices
        except Exception as e:
            logger.error(f"Error loading fallback cache: {e}")
            return []

    def _update_cache(self, prices: list[MarketPrice]) -> None:
        try:
            existing_data = []
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    try:
                        existing_data = json.load(f)
                    except json.JSONDecodeError:
                        pass
            
            # Convert models to dicts
            new_data = []
            for p in prices:
                d = p.model_dump()
                d['arrival_date'] = d['arrival_date'].isoformat()
                d['fetched_at'] = d['fetched_at'].isoformat()
                d['min_price'] = str(d['min_price'])
                d['max_price'] = str(d['max_price'])
                d['modal_price'] = str(d['modal_price'])
                new_data.append(d)
                
            # Merge and save
            merged_data = [item for item in existing_data if item.get('commodity') != prices[0].commodity] + new_data
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(merged_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error updating cache: {e}")

    def _check_staleness(self, prices: list[MarketPrice]) -> list[str]:
        warnings = []
        yesterday = datetime.now() - timedelta(days=1)
        for price in prices:
            if price.fetched_at < yesterday:
                warnings.append(f"Price for {price.market_name} is older than 24 hours.")
        return warnings

    def get_prices(self, commodity: str, state: str = 'Tamil Nadu') -> tuple[list[MarketPrice], list[str]]:
        prices = self.fetch_live_prices(commodity, state)
        warnings = self._check_staleness(prices)
        return prices, warnings

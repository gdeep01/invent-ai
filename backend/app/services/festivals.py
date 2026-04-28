from datetime import date, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models import Festival


# Default India festivals - can be customized per store/region
DEFAULT_FESTIVALS = [
    # Diwali (dates vary by year - these are approximate)
    {"name": "Diwali", "month": 10, "day": 24, "impact_multiplier": 2.5, "region": "All India"},
    {"name": "Dhanteras", "month": 10, "day": 22, "impact_multiplier": 1.8, "region": "All India"},
    
    # Holi
    {"name": "Holi", "month": 3, "day": 14, "impact_multiplier": 1.6, "region": "North India"},
    
    # Eid (approximate - lunar calendar)
    {"name": "Eid ul-Fitr", "month": 4, "day": 10, "impact_multiplier": 2.0, "region": "All India"},
    {"name": "Eid ul-Adha", "month": 6, "day": 17, "impact_multiplier": 1.8, "region": "All India"},
    
    # Ganesh Chaturthi
    {"name": "Ganesh Chaturthi", "month": 9, "day": 7, "impact_multiplier": 1.7, "region": "Maharashtra"},
    
    # Navratri / Durga Puja
    {"name": "Navratri Start", "month": 10, "day": 3, "impact_multiplier": 1.5, "region": "All India"},
    {"name": "Durga Puja", "month": 10, "day": 12, "impact_multiplier": 2.0, "region": "West Bengal"},
    
    # Pongal / Makar Sankranti
    {"name": "Pongal", "month": 1, "day": 14, "impact_multiplier": 1.6, "region": "Tamil Nadu"},
    {"name": "Makar Sankranti", "month": 1, "day": 14, "impact_multiplier": 1.5, "region": "North India"},
    
    # Onam
    {"name": "Onam", "month": 8, "day": 29, "impact_multiplier": 1.8, "region": "Kerala"},
    
    # Christmas & New Year
    {"name": "Christmas", "month": 12, "day": 25, "impact_multiplier": 1.5, "region": "All India"},
    {"name": "New Year", "month": 1, "day": 1, "impact_multiplier": 1.4, "region": "All India"},
    
    # Raksha Bandhan
    {"name": "Raksha Bandhan", "month": 8, "day": 19, "impact_multiplier": 1.5, "region": "North India"},
]


class FestivalService:
    def __init__(self, db: Session):
        self.db = db

    def seed_default_festivals(self, year: int = 2026) -> int:
        count = 0
        for fest in DEFAULT_FESTIVALS:
            try:
                festival_date = date(year, fest["month"], fest["day"])

                existing = self.db.query(Festival).filter(
                    Festival.name == fest["name"],
                    Festival.date == festival_date
                ).first()
                if not existing:
                    festival = Festival(
                        name=fest["name"],
                        date=festival_date,
                        region=fest["region"],
                        impact_multiplier=fest["impact_multiplier"],
                    )
                    self.db.add(festival)
                    count += 1
            except ValueError:
                continue

        self.db.commit()
        return count

    def get_festivals_in_range(self, start_date: date, end_date: date, region: Optional[str] = None) -> List[Festival]:
        query = self.db.query(Festival).filter(
            Festival.date >= start_date,
            Festival.date <= end_date
        )
        if region:
            query = query.filter((Festival.region == region) | (Festival.region == "All India"))
        return query.order_by(Festival.date).all()

    def get_festival_dates_dict(self, start_date: date, end_date: date) -> Dict[date, str]:
        festivals = self.get_festivals_in_range(start_date, end_date)
        result = {}
        for fest in festivals:
            for delta in range(-2, 3):
                fest_date = fest.date + timedelta(days=delta)
                if start_date <= fest_date <= end_date:
                    if fest_date not in result:
                        result[fest_date] = fest.name
        return result

    def get_impact_multiplier(self, target_date: date) -> float:
        for delta in range(-2, 3):
            check_date = target_date + timedelta(days=-delta)
            festival = self.db.query(Festival).filter(Festival.date == check_date).first()
            if festival:
                distance_factor = 1.0 - (abs(delta) * 0.2)
                return festival.impact_multiplier * distance_factor
        return 1.0

    def get_upcoming_festivals(self, start_date: date, days: int = 30) -> List[Festival]:
        return self.get_festivals_in_range(start_date, start_date + timedelta(days=days))

    def add_festival(
        self,
        name: str,
        festival_date: date,
        region: Optional[str] = "All India",
        impact_multiplier: float = 1.5,
        category: Optional[str] = None,
    ) -> Festival:
        festival = Festival(
            name=name,
            date=festival_date,
            region=region,
            impact_multiplier=impact_multiplier,
            category=category,
        )
        self.db.add(festival)
        self.db.commit()
        return festival

    def get_all_festivals(self) -> List[Festival]:
        return self.db.query(Festival).order_by(Festival.date).all()

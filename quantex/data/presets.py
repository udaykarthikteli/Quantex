"""
Industry Scenario Presets for Hackathon Use Cases:
1. E-Commerce Last-Mile Express
2. Postal / Courier Hub Dispatch
3. Field Services & Maintenance Fleets
4. Municipal Smart Collection
"""

from typing import Dict, List
from quantex.core.problem_model import RoutingProblem, DeliveryNode, Vehicle


def get_ecommerce_preset() -> RoutingProblem:
    """
    E-Commerce Urban Fast Delivery:
    Central fulfillment depot with mixed residential & commercial stops.
    """
    nodes = [
        DeliveryNode(0, "Central Fulfillment Depot", 17.7215, 83.3060, demand=0.0, is_depot=True),
        DeliveryNode(1, "Tech Hub Sector 1", 17.7340, 83.3180, demand=12.0, time_window_start=30, time_window_end=120),
        DeliveryNode(2, "Harbor Commercial Area", 17.7020, 83.2980, demand=18.0, time_window_start=60, time_window_end=180),
        DeliveryNode(3, "Suburban Heights Block A", 17.7480, 83.3320, demand=8.0, time_window_start=90, time_window_end=240),
        DeliveryNode(4, "Metro Plaza Mall", 17.7150, 83.3250, demand=15.0, time_window_start=45, time_window_end=150),
        DeliveryNode(5, "Green Valley Residences", 17.7560, 83.2850, demand=10.0, time_window_start=120, time_window_end=300),
        DeliveryNode(6, "Airport Gateway Logistics", 17.7310, 83.2450, demand=22.0, time_window_start=60, time_window_end=210)
    ]

    vehicles = [
        Vehicle(1, "Electric Express Van 1", capacity=45.0, vehicle_type="Electric_Van", emission_factor_g_km=45.0, avg_speed_kmh=38.0, cost_per_km=0.8),
        Vehicle(2, "Electric Express Van 2", capacity=45.0, vehicle_type="Electric_Van", emission_factor_g_km=45.0, avg_speed_kmh=38.0, cost_per_km=0.8)
    ]

    return RoutingProblem(nodes=nodes, vehicles=vehicles)


def get_postal_preset() -> RoutingProblem:
    """
    Postal / Courier Distribution:
    Regional sorting hub dispatching to neighborhood post offices and locker hubs.
    """
    nodes = [
        DeliveryNode(0, "Central Post & Parcel Hub", 18.1124, 83.3970, demand=0.0, is_depot=True),
        DeliveryNode(1, "Post Office North Branch", 18.1350, 83.4120, demand=25.0),
        DeliveryNode(2, "Post Office East Gate", 18.0980, 83.4350, demand=30.0),
        DeliveryNode(3, "University Campus Locker", 18.1250, 83.3750, demand=15.0),
        DeliveryNode(4, "Railway Station Postal Annex", 18.1050, 83.3910, demand=35.0),
        DeliveryNode(5, "West Suburb Parcel Box", 18.0820, 83.3650, demand=20.0)
    ]

    vehicles = [
        Vehicle(1, "Postal Diesel Van 101", capacity=70.0, vehicle_type="Diesel_Van", emission_factor_g_km=185.0, avg_speed_kmh=35.0, cost_per_km=1.2),
        Vehicle(2, "Postal Cargo EV 102", capacity=70.0, vehicle_type="Electric_Van", emission_factor_g_km=45.0, avg_speed_kmh=35.0, cost_per_km=0.8)
    ]

    return RoutingProblem(nodes=nodes, vehicles=vehicles)


def get_field_services_preset() -> RoutingProblem:
    """
    Field Services & Emergency Appliance/Network Repair Fleet.
    """
    nodes = [
        DeliveryNode(0, "Technical Dispatch Center", 17.7400, 83.3100, demand=0.0, is_depot=True),
        DeliveryNode(1, "Hospital Solar Grid Repair", 17.7550, 83.3250, demand=1.0, priority=5, service_duration=45.0),
        DeliveryNode(2, "Fiber Optic Junction 4", 17.7250, 83.3400, demand=1.0, priority=4, service_duration=30.0),
        DeliveryNode(3, "Commercial HVAC Maintenance", 17.7100, 83.2800, demand=1.0, priority=2, service_duration=60.0),
        DeliveryNode(4, "Residential Smart Meter Setup", 17.7600, 83.2950, demand=1.0, priority=3, service_duration=20.0)
    ]

    vehicles = [
        Vehicle(1, "Service Van - Team Alpha", capacity=10.0, vehicle_type="Diesel_Van", emission_factor_g_km=180.0, avg_speed_kmh=40.0, cost_per_km=1.4),
        Vehicle(2, "Service Van - Team Beta", capacity=10.0, vehicle_type="Electric_Van", emission_factor_g_km=45.0, avg_speed_kmh=40.0, cost_per_km=0.9)
    ]

    return RoutingProblem(nodes=nodes, vehicles=vehicles)


def get_municipal_preset() -> RoutingProblem:
    """
    Municipal Smart Waste Collection:
    Depot + smart bin collection points with sensor fill-levels.
    """
    nodes = [
        DeliveryNode(0, "Municipal Sanitation Base", 17.6850, 83.2100, demand=0.0, is_depot=True),
        DeliveryNode(1, "Market Organic Waste Bin", 17.7050, 83.2350, demand=40.0),
        DeliveryNode(2, "Industrial Zone Dumpster", 17.6650, 83.2550, demand=60.0),
        DeliveryNode(3, "Civic Center Recycling Station", 17.7200, 83.2700, demand=35.0),
        DeliveryNode(4, "Beach Promenade Bin Cluster", 17.7120, 83.3300, demand=50.0),
        DeliveryNode(5, "Old Town Collection Point", 17.6950, 83.2950, demand=45.0)
    ]

    vehicles = [
        Vehicle(1, "Heavy Compactor Truck 1", capacity=120.0, vehicle_type="Gas_Truck", emission_factor_g_km=260.0, avg_speed_kmh=25.0, cost_per_km=2.1),
        Vehicle(2, "Heavy Compactor Truck 2", capacity=120.0, vehicle_type="Gas_Truck", emission_factor_g_km=260.0, avg_speed_kmh=25.0, cost_per_km=2.1)
    ]

    return RoutingProblem(nodes=nodes, vehicles=vehicles)


PRESETS = {
    "E-Commerce Last-Mile Express": get_ecommerce_preset,
    "Postal & Courier Dispatch": get_postal_preset,
    "Field Services & Technician Dispatch": get_field_services_preset,
    "Municipal Waste Collection": get_municipal_preset
}

"""Monitoring API endpoints with enhanced features."""

from typing import Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from utils.enhanced_monitoring import (
    ActiveTask,
    SystemAlert,
    SystemMetrics,
    get_monitor,
)

router = APIRouter(prefix="/api/system", tags=["monitoring"])


class SystemStatus(BaseModel):
    """System status response model"""

    health_score: float
    metrics: SystemMetrics
    alerts: List[SystemAlert]
    tasks: List[ActiveTask]
    analytics: Dict[str, float]


@router.get("/status", response_model=SystemStatus)
async def get_system_status():
    """Get comprehensive system status"""
    try:
        monitor = get_monitor()
        return SystemStatus(
            health_score=monitor.get_system_health_score(),
            metrics=monitor.get_current_metrics(),
            alerts=monitor.get_active_alerts(),
            tasks=monitor.get_active_tasks(),
            analytics=monitor.get_performance_analytics(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", response_model=SystemMetrics)
async def get_current_metrics():
    """Get current system metrics"""
    try:
        return get_monitor().get_current_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts", response_model=List[SystemAlert])
async def get_alerts():
    """Get active system alerts"""
    try:
        return get_monitor().get_active_alerts()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks", response_model=List[ActiveTask])
async def get_tasks():
    """Get active tasks"""
    try:
        return get_monitor().get_active_tasks()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics")
async def get_analytics():
    """Get system performance analytics"""
    try:
        return get_monitor().get_performance_analytics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_metrics_history(duration: int = 3600):
    """Get historical metrics for the specified duration in seconds"""
    try:
        history = get_monitor().get_metrics_history(duration)
        return {
            "metrics": [m[0].model_dump() for m in history],
            "performance": [m[1].model_dump() for m in history],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

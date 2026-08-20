from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import register, telemetry, commands, firewall, nodes_read, anomaly

app = FastAPI(title="Argus Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(register.router)
app.include_router(telemetry.router)
app.include_router(commands.router)
app.include_router(firewall.router)
app.include_router(nodes_read.router)
app.include_router(anomaly.router)
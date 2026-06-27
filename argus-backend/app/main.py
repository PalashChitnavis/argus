from fastapi import FastAPI
from app.routers import register, telemetry, telemetry_read, commands, firewall

app = FastAPI(title="Argus Backend")

app.include_router(register.router)
app.include_router(telemetry.router)
app.include_router(telemetry_read.router)
app.include_router(commands.router)
app.include_router(firewall.router)
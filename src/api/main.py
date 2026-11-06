from fastapi import FastAPI

app = FastAPI(
    title="FitZone - Componentes de Lógica de Negocio",
    description="API del PIA: membresías, reservas y listas de espera de FitZone.",
    version="0.1.0",
)


@app.get("/health", tags=["sistema"])
def health() -> dict:
    return {"status": "ok"}

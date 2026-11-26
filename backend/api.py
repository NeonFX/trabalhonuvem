"""API REST responsável por cadastro, consulta e exclusão de monitores."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import db
from probe import validate_target


@asynccontextmanager
async def lifespan(app):
    db.initialize()
    yield


app = FastAPI(title='Uptime Monitor', version='1.0', lifespan=lifespan)


class SiteInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    url: str = Field(min_length=1, max_length=2048)


@app.get('/api/health')
def health():
    try:
        db.health()
    except Exception:
        raise HTTPException(503, 'Banco indisponível')
    return {'status': 'ok'}


@app.get('/api/sites')
def sites():
    return db.list_sites()


@app.post('/api/sites', status_code=201)
def add_site(data: SiteInput):
    try:
        name = data.name.strip()
        if not name:
            raise ValueError('Informe um nome.')
        url = validate_target(data.url)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    site = db.create_site(name, url)
    if not site:
        raise HTTPException(409, 'Esta URL já está cadastrada.')
    return site


@app.post('/api/demo')
def demo():
    created = []
    for name, url in [('Demo · disponível', 'http://web/demo/online'), ('Demo · indisponível', 'http://web/demo/offline')]:
        site = db.create_site(name, url)
        if site:
            created.append(site)
    return {'created': created}


@app.get('/api/sites/{site_id}/history')
def site_history(site_id: int):
    result = db.history(site_id)
    if result is None:
        raise HTTPException(404, 'Monitor não encontrado.')
    return result


@app.delete('/api/sites/{site_id}', status_code=204)
def remove_site(site_id: int):
    if not db.delete_site(site_id):
        raise HTTPException(404, 'Monitor não encontrado.')

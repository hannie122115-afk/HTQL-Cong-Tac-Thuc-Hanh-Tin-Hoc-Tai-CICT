from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from database import get_connection
from fastapi.responses import RedirectResponse

app = FastAPI()

templates = Jinja2Templates(directory="templates")

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )

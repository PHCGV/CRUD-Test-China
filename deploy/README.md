# Deploy 

## 0) Stack Docker local (backend + frontend + Oracle)

1. Subir stack com build:

```bash
docker compose --env-file .env.docker up -d --build
```

2. Verifique status e logs:

```bash
docker compose --env-file .env.docker ps
docker compose --env-file .env.docker logs -f backend
```

3. Acesso local:
- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8050`
- Oracle: `localhost:1522/XEPDB1` 

4. Parar stack:

```bash
docker compose --env-file .env.docker down
```

5. Reset completo do banco local (remove volume):

```bash
docker compose --env-file .env.docker down -v
```


## 1) Higienizacao de temporarios locais

Para mapear arquivos temporarios candidatos a descarte sem apagar nada:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\cleanup-temp-files.ps1
```

Para remover apenas candidatos nao rastreados pelo git:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\cleanup-temp-files.ps1 -Delete
```

## 2) Executar API localmente 

```bash
uvicorn main:app 
```


## 3) Nginx

```bash
nginx -t
systemctl reload nginx
```

## 4) Ngrok 


1. No `.env`, habilitar suporte ao host/origem ngrok no backend:

```env
ENABLE_NGROK=true
```

2. Iniciar a API local (porta 8050) e depois upar:

```powershell
ngrok http 8050
```

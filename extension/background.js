const CONFIG_KEY = 'citychina_config'
const SESSION_KEY = 'citychina_session'

const DEFAULT_CONFIG = {
    apiBase: 'http://127.0.0.1:8050',
    idModalidade: 1,
    pesoDefault: 300,
    valorDefault: 1,
}

const TRUSTED_EXTERNAL_SENDER_PATTERNS = [
    /^https:\/\/phcgv-import\.vercel\.app(\/|$)/i,
    /^http:\/\/127\.0\.0\.1:8050(\/|$)/i,
    /^http:\/\/localhost:8050(\/|$)/i,
    /^http:\/\/127\.0\.0\.1:5173(\/|$)/i,
    /^http:\/\/localhost:5173(\/|$)/i,
    /^https:\/\/[a-z0-9-]+\.ngrok-free\.app(\/|$)/i,
    /^https:\/\/[a-z0-9-]+\.ngrok\.app(\/|$)/i,
    /^https:\/\/[a-z0-9-]+\.ngrok\.io(\/|$)/i,
    /^https:\/\/[a-z0-9-]+\.ngrok-free\.dev(\/|$)/i,
    /^https:\/\/[a-z0-9-]+\.ngrok\.dev(\/|$)/i,
]

function normalizeApiBase(value) {
    const raw = String(value || '').trim()
    const safe = raw || DEFAULT_CONFIG.apiBase
    return safe.replace(/\/+$/, '')
}

function toPositiveNumber(value, fallback) {
    const num = Number(value)
    if (!Number.isFinite(num) || num <= 0) return fallback
    return num
}

function toInt(value, fallback) {
    const num = Number(value)
    if (!Number.isInteger(num) || num <= 0) return fallback
    return num
}

function parsePrice(value) {
    if (value === null || value === undefined) return null
    if (typeof value === 'number') {
        return Number.isFinite(value) && value > 0 ? value : null
    }

    let text = String(value).trim()
    if (!text) return null

    text = text.replace(/[^\d,\.]/g, '')
    if (!text) return null

    if (text.includes(',') && text.includes('.')) {
        text = text.replace(/\./g, '').replace(',', '.')
    } else if (text.includes(',')) {
        text = text.replace(',', '.')
    }

    const num = Number(text)
    return Number.isFinite(num) && num > 0 ? num : null
}

function firstNonEmpty(...values) {
    for (const value of values) {
        const text = String(value || '').trim()
        if (text) return text
    }
    return ''
}

function truncateUtf8Bytes(text, maxBytes) {
    const raw = String(text || '').trim()
    if (!raw) return ''

    const encoder = new TextEncoder()
    let bytes = encoder.encode(raw)
    if (bytes.length <= maxBytes) return raw

    let end = raw.length
    while (end > 0) {
        end -= 1
        const candidate = raw.slice(0, end).trim()
        bytes = encoder.encode(candidate)
        if (bytes.length <= maxBytes) return candidate
    }

    return ''
}

function isVendorPage(data) {
    if (String(data.pageType || '').toLowerCase() === 'vendedor') return true

    const url = String(data.url || '').toLowerCase()
    return /seller|shop|store|user|profile|vendedor|loja/.test(url)
}

async function getConfig() {
    const data = await chrome.storage.local.get(CONFIG_KEY)
    const saved = data[CONFIG_KEY] || {}

    return {
        apiBase: normalizeApiBase(saved.apiBase),
        idModalidade: toInt(saved.idModalidade, DEFAULT_CONFIG.idModalidade),
        pesoDefault: toPositiveNumber(saved.pesoDefault, DEFAULT_CONFIG.pesoDefault),
        valorDefault: toPositiveNumber(saved.valorDefault, DEFAULT_CONFIG.valorDefault),
    }
}

async function saveConfig(config) {
    const next = {
        apiBase: normalizeApiBase(config.apiBase),
        idModalidade: toInt(config.idModalidade, DEFAULT_CONFIG.idModalidade),
        pesoDefault: toPositiveNumber(config.pesoDefault, DEFAULT_CONFIG.pesoDefault),
        valorDefault: toPositiveNumber(config.valorDefault, DEFAULT_CONFIG.valorDefault),
    }

    await chrome.storage.local.set({ [CONFIG_KEY]: next })
    return next
}

async function getSession() {
    const data = await chrome.storage.local.get(SESSION_KEY)
    return data[SESSION_KEY] || null
}

async function saveSession(session) {
    await chrome.storage.local.set({ [SESSION_KEY]: session })
}

async function clearSession() {
    await chrome.storage.local.remove(SESSION_KEY)
}

function isTrustedExternalSender(url) {
    const senderUrl = String(url || '').trim()
    if (!senderUrl) return false
    return TRUSTED_EXTERNAL_SENDER_PATTERNS.some((pattern) => pattern.test(senderUrl))
}

async function callApi(path, options = {}) {
    const {
        baseUrl,
        token,
        method = 'GET',
        body,
    } = options

    const headers = { 'Content-Type': 'application/json' }
    if (token) headers.Authorization = `Bearer ${token}`

    const response = await fetch(`${baseUrl}${path}`, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
    })

    let data = null
    try {
        data = await response.json()
    } catch {
        data = null
    }

    if (response.status === 401 && token) {
        await clearSession()
    }

    return { response, data }
}

function responseErrorMessage(data, fallback) {
    if (!data) return fallback
    if (typeof data.detail === 'string') {
        if (data.detail.toLowerCase().includes('token de acesso invalido')) {
            return 'Sessao expirada na extensao. Faca login novamente no popup.'
        }
        return data.detail
    }
    return fallback
}

function normalizeModalidades(data) {
    if (!Array.isArray(data)) return []

    return data
        .map((item) => {
            const id = Number(item?.id_modalidade)
            const nome = String(item?.nome_modalidade || '').trim()
            if (!Number.isInteger(id) || id <= 0 || !nome) return null
            return {
                id_modalidade: id,
                nome_modalidade: nome,
            }
        })
        .filter(Boolean)
}

function createVendorPayload(scraped) {
    const nome = firstNonEmpty(scraped.vendorName, scraped.storeName, scraped.title, 'Vendedor importado')
    const loja = firstNonEmpty(scraped.storeName, scraped.vendorName, scraped.host, 'Loja importada')
    const linkLoja = isVendorPage(scraped)
        ? firstNonEmpty(scraped.storeLink, scraped.url)
        : firstNonEmpty(scraped.storeLink)

    return {
        nome,
        loja,
        link_loja: linkLoja || null,
    }
}

async function ensureVendorForProduct(scraped, config, session) {
    const storeName = firstNonEmpty(scraped.storeName, scraped.vendorName)
    if (!storeName) return null

    const { response: listResponse, data: sellers } = await callApi('/vendedor/', {
        baseUrl: config.apiBase,
        token: session.token,
    })

    if (listResponse.ok && Array.isArray(sellers)) {
        const target = storeName.toLowerCase()
        const found = sellers.find((seller) => {
            const nome = String(seller.nome || '').toLowerCase()
            const loja = String(seller.loja || '').toLowerCase()
            return nome === target || loja === target
        })

        if (found && found.id_vendedor) return found.id_vendedor
    }

    const payload = createVendorPayload(scraped)
    const { response: createResponse, data: created } = await callApi('/vendedor/', {
        baseUrl: config.apiBase,
        token: session.token,
        method: 'POST',
        body: payload,
    })

    if (!createResponse.ok) return null
    return created?.id_vendedor || null
}

async function saveVendor(scraped, config, session) {
    const payload = createVendorPayload(scraped)

    const { response, data } = await callApi('/vendedor/', {
        baseUrl: config.apiBase,
        token: session.token,
        method: 'POST',
        body: payload,
    })

    if (!response.ok) {
        return {
            ok: false,
            message: responseErrorMessage(data, 'Nao foi possivel salvar o vendedor.'),
        }
    }

    return {
        ok: true,
        message: 'Vendedor salvo com sucesso.',
        payload: data,
    }
}

async function saveProduct(scraped, config, session) {
    const idVendedor = await ensureVendorForProduct(scraped, config, session)
    const valor = parsePrice(scraped.price) || config.valorDefault
    const pesoOverride = toInt(scraped.overridePeso, 0)
    const modalidadeOverride = toInt(scraped.overrideModalidadeId, 0)

    const payload = {
        nome: truncateUtf8Bytes(firstNonEmpty(scraped.productName, scraped.title, 'Produto importado'), 200),
        link_produto: firstNonEmpty(scraped.productLink, scraped.url),
        link_imagem: firstNonEmpty(scraped.imageUrl) || null,
        valor,
        peso: pesoOverride > 0 ? pesoOverride : config.pesoDefault,
        id_modalidade: modalidadeOverride > 0 ? modalidadeOverride : config.idModalidade,
        id_vendedor: idVendedor,
    }

    const { response, data } = await callApi('/produto/', {
        baseUrl: config.apiBase,
        token: session.token,
        method: 'POST',
        body: payload,
    })

    if (!response.ok) {
        return {
            ok: false,
            message: responseErrorMessage(
                data,
                'Nao foi possivel salvar o produto. Verifique modalidade/peso/valor no popup da extensao.',
            ),
        }
    }

    return {
        ok: true,
        message: 'Produto salvo com sucesso.',
        payload: data,
    }
}

async function saveScrapedPage(scraped) {
    const config = await getConfig()
    const session = await getSession()

    if (!session?.token) {
        return {
            ok: false,
            message: 'Faca login na extensao antes de salvar.',
        }
    }

    const isVendor = isVendorPage(scraped)
    const result = isVendor
        ? await saveVendor(scraped, config, session)
        : await saveProduct(scraped, config, session)

    return result
}

async function getProductFormData() {
    const config = await getConfig()
    const session = await getSession()

    if (!session?.token) {
        return {
            ok: false,
            message: 'Faca login na extensao antes de carregar modalidades.',
            config,
            modalidades: [],
        }
    }

    const { response, data } = await callApi('/modalidade/', {
        baseUrl: config.apiBase,
        token: session.token,
    })

    if (!response.ok) {
        return {
            ok: false,
            message: responseErrorMessage(data, 'Nao foi possivel carregar modalidades.'),
            config,
            modalidades: [],
        }
    }

    return {
        ok: true,
        config,
        modalidades: normalizeModalidades(data),
    }
}

async function syncSessionFromMainApp(payload, sender) {
    const senderUrl = String(sender?.url || '')
    if (!isTrustedExternalSender(senderUrl)) {
        return { ok: false, message: 'Origem nao autorizada para sincronizar sessao da extensao.' }
    }

    const token = String(payload?.token || '').trim()
    if (!token) {
        return { ok: false, message: 'Token de extensao ausente.' }
    }

    const config = await getConfig()
    const nextApiBase = normalizeApiBase(payload?.apiBase || config.apiBase)
    if (nextApiBase !== config.apiBase) {
        await saveConfig({ ...config, apiBase: nextApiBase })
    }

    const { response, data } = await callApi('/auth/me', {
        baseUrl: nextApiBase,
        token,
    })

    if (!response.ok) {
        return {
            ok: false,
            message: responseErrorMessage(data, 'Nao foi possivel validar sessao recebida do sistema principal.'),
        }
    }

    const session = {
        token,
        user: data,
        source: 'main-app',
        synced_at: new Date().toISOString(),
    }

    await saveSession(session)

    return {
        ok: true,
        message: 'Sessao da extensao sincronizada com sucesso.',
        session,
    }
}

async function loginInApi(credentials) {
    const config = await getConfig()
    const username = String(credentials.username || '').trim()
    const senha = String(credentials.senha || '')
    const apiBase = normalizeApiBase(credentials.apiBase || config.apiBase)

    if (!username || !senha) {
        return { ok: false, message: 'Informe usuario e senha.' }
    }

    if (apiBase !== config.apiBase) {
        await saveConfig({ ...config, apiBase })
    }

    const { response, data } = await callApi('/auth/login', {
        baseUrl: apiBase,
        method: 'POST',
        body: { username, senha },
    })

    if (!response.ok || !data?.access_token) {
        return {
            ok: false,
            message: responseErrorMessage(data, 'Falha no login da extensao.'),
        }
    }

    const token = data.access_token
    const meResult = await callApi('/auth/me', {
        baseUrl: apiBase,
        token,
    })

    if (!meResult.response.ok) {
        return {
            ok: false,
            message: 'Token recebido, mas nao foi possivel validar sessao.',
        }
    }

    const session = {
        token,
        user: meResult.data,
    }

    await saveSession(session)

    return {
        ok: true,
        message: 'Login realizado com sucesso.',
        session,
    }
}

async function getState() {
    const config = await getConfig()
    const session = await getSession()

    return {
        ok: true,
        config,
        session,
    }
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    const run = async () => {
        const action = request?.action

        if (action === 'extension:get-state') {
            return getState()
        }

        if (action === 'extension:update-config') {
            const nextConfig = await saveConfig(request.config || {})
            return { ok: true, message: 'Configuracao salva.', config: nextConfig }
        }

        if (action === 'extension:login') {
            return loginInApi(request.credentials || {})
        }

        if (action === 'extension:logout') {
            await clearSession()
            return { ok: true, message: 'Sessao encerrada.' }
        }

        if (action === 'extension:save-page') {
            return saveScrapedPage(request.scraped || {})
        }

        if (action === 'extension:get-product-form-data') {
            return getProductFormData()
        }

        return { ok: false, message: 'Acao da extensao nao suportada.' }
    }

    run()
        .then((result) => sendResponse(result))
        .catch((error) => {
            sendResponse({
                ok: false,
                message: String(error?.message || error || 'Erro interno na extensao.'),
            })
        })

    return true
})

chrome.runtime.onMessageExternal.addListener((request, sender, sendResponse) => {
    const run = async () => {
        const action = request?.action

        if (action === 'extension:sync-session') {
            return syncSessionFromMainApp(request, sender)
        }

        return { ok: false, message: 'Acao externa nao suportada.' }
    }

    run()
        .then((result) => sendResponse(result))
        .catch((error) => {
            sendResponse({
                ok: false,
                message: String(error?.message || error || 'Erro interno na sincronizacao externa.'),
            })
        })

    return true
})
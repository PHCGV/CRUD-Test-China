function findMeta(selector) {
    const node = document.querySelector(selector)
    const value = node?.content || node?.getAttribute('content') || ''
    return String(value).trim()
}

function normalizeText(value) {
    return String(value || '').replace(/\s+/g, ' ').trim()
}

function readNodeText(node) {
    if (!node) return ''
    return normalizeText(node.innerText || node.textContent || '')
}

function isVisibleElement(node) {
    if (!node || !(node instanceof Element)) return false
    const style = window.getComputedStyle(node)
    if (style.display === 'none' || style.visibility === 'hidden') return false
    const rect = node.getBoundingClientRect()
    return rect.width > 0 && rect.height > 0
}

function sanitizeTitleText(text) {
    let value = normalizeText(text)
    if (!value) return ''

    // Drop trailing site/section suffixes usually appended to document titles.
    value = value.replace(/\s*[|\-\u2014\u2013]\s*(goofish|xianyu|taobao|alibaba).*/i, '').trim()

    const splitCandidates = [' | ', ' - ', ' -', '|', ' - ', ' :: ']
    for (const token of splitCandidates) {
        if (value.includes(token)) {
            const first = normalizeText(value.split(token)[0])
            if (first.length >= 4) {
                value = first
                break
            }
        }
    }

    return value
}

function isLikelyProductName(text) {
    const value = normalizeText(text)
    if (!value) return false
    if (value.length < 2) return false
    if (/^(\u00A5|yuan|cny|r\$|\$)/i.test(value)) return false
    if (/^[\d\s.,]+$/.test(value)) return false
    return true
}

function isPriceText(text) {
    return /(?:\u00A5|¥|yuan|cny|r\$|\$)\s*[\d.,]+/i.test(String(text || ''))
}

function isRecommendationContext(node) {
    let current = node
    for (let depth = 0; current && depth < 7; depth += 1) {
        const className = String(current.className || '').toLowerCase()
        const id = String(current.id || '').toLowerCase()
        const role = String(current.getAttribute?.('role') || '').toLowerCase()
        const aria = String(current.getAttribute?.('aria-label') || '').toLowerCase()
        const marker = `${className} ${id} ${role} ${aria}`

        if (/(feeds-content|row1-wrap-title|main-title|recommend|guess|similar|related|tuijian|猜你喜欢|推荐|为你推荐)/i.test(marker)) {
            return true
        }

        current = current.parentElement
    }
    return false
}

function findStrictMainNameNode() {
    const strictSelectors = [
        'div[class*="notLoginContainer"] div[class^="main--"] span[class^="desc--"] > span > span',
        'div[class*="notLoginContainer"] div[class^="main--"] span[class^="desc--"] > span',
        'div[class*="notLoginContainer"] div[class^="main--"] span[class^="desc--"]',
        'div[class^="main--"] span[class^="desc--"] > span > span',
        'div[class^="main--"] span[class^="desc--"] > span',
        'div[class^="main--"] span[class^="desc--"]',
    ]

    for (const selector of strictSelectors) {
        const nodes = document.querySelectorAll(selector)
        for (const node of nodes) {
            if (!(node instanceof Element)) continue
            if (!isVisibleElement(node)) continue
            if (isRecommendationContext(node)) continue
            const text = readNodeText(node)
            if (!isLikelyProductName(text)) continue
            return node
        }
    }

    return null
}

function findPrimaryPriceNode() {
    const selectors = [
        '[data-price]',
        '[class*="price"]',
        '[class*="amount"]',
    ]

    const matches = []
    for (const selector of selectors) {
        const nodes = document.querySelectorAll(selector)
        for (const node of nodes) {
            if (!(node instanceof Element)) continue
            if (!isVisibleElement(node)) continue
            const text = readNodeText(node)
            if (!isPriceText(text)) continue

            const rect = node.getBoundingClientRect()
            let score = 0
            if (rect.top >= -120 && rect.top <= 520) score += 20
            if (rect.top > 520) score -= 6
            if (rect.top < -120) score -= 10
            if (isRecommendationContext(node)) score -= 20

            matches.push({ node, score, top: rect.top })
        }
    }

    if (!matches.length) return null

    matches.sort((a, b) => {
        if (b.score !== a.score) return b.score - a.score
        return Math.abs(a.top) - Math.abs(b.top)
    })

    return matches[0].node
}

function extractNameFromPriceBlock(priceNode) {
    let current = priceNode
    for (let depth = 0; current && depth < 6; depth += 1) {
        const blockText = normalizeText(current.innerText || '')
        if (blockText.length >= 20 && blockText.length <= 1200) {
            const lines = String(current.innerText || '')
                .split('\n')
                .map((line) => normalizeText(line))
                .filter(Boolean)

            for (const line of lines) {
                if (!line) continue
                if (isPriceText(line)) continue
                if (/(浏览|余量|包邮|展开|推荐|为你推荐)/i.test(line)) continue
                if (!isLikelyProductName(line)) continue
                if (line.length > 160) continue
                return line
            }
        }

        current = current.parentElement
    }

    return ''
}

function findText(selectors) {
    for (const selector of selectors) {
        const node = document.querySelector(selector)
        const text = readNodeText(node)
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

function extractProductName(titleFallback) {
    const candidates = []
    const strictMainNameNode = findStrictMainNameNode()
    const priceNode = findPrimaryPriceNode()

    if (strictMainNameNode) {
        const strictName = truncateUtf8Bytes(sanitizeTitleText(readNodeText(strictMainNameNode)), 200)
        if (strictName) return strictName
    }

    const priceRect = priceNode?.getBoundingClientRect?.() || null

    function addCandidate(rawText, node, weight, visible) {
        const text = sanitizeTitleText(rawText)
        if (!isLikelyProductName(text)) return

        let score = weight
        const len = text.length
        if (len >= 8 && len <= 140) score += 20
        if (len > 140) score -= 6
        if (!visible) score -= 8
        if (/(shop|store|seller|vendedor)/i.test(text)) score -= 8
        if (/(goofish|xianyu|taobao|alibaba)/i.test(text)) score -= 5
        if (node && isRecommendationContext(node)) score -= 35

        if (node && priceRect) {
            const rect = node.getBoundingClientRect()
            const distance = Math.abs(rect.top - priceRect.top)
            if (distance <= 240) score += 26
            else if (distance <= 520) score += 10
            else if (distance > 980) score -= 16

            if (rect.top > 900) score -= 20
            if (rect.top < -120) score -= 10
        }

        candidates.push({ text, score })
    }

    if (priceNode) {
        const fromPriceBlock = extractNameFromPriceBlock(priceNode)
        addCandidate(fromPriceBlock, priceNode, 110, true)
    }

    const exactSelector = 'span[data-spm-anchor-id="a21ybx.item.0.i1.3c013da6EW9RVj"]'
    const exactNodes = document.querySelectorAll(exactSelector)
    for (const node of exactNodes) {
        addCandidate(readNodeText(node), node, 100, isVisibleElement(node))
    }

    const prioritizedSelectors = [
        '[data-spm-anchor-id^="a21ybx.item.0.i"] span[class^="desc--"]',
        'span[data-spm-anchor-id^="a21ybx.item.0.i"]',
        'span[class^="desc--"] > span > span',
        'span[class^="desc--"] > span',
        'span[class^="desc--"]',
        'h1',
    ]

    for (const selector of prioritizedSelectors) {
        const nodes = document.querySelectorAll(selector)
        const limit = Math.min(nodes.length, 8)
        for (let i = 0; i < limit; i += 1) {
            const node = nodes[i]
            addCandidate(readNodeText(node), node, 60 - i, isVisibleElement(node))
        }
    }

    addCandidate(titleFallback, null, 20, true)

    if (!candidates.length) {
        return truncateUtf8Bytes(sanitizeTitleText(titleFallback), 200)
    }

    candidates.sort((a, b) => b.score - a.score)
    return truncateUtf8Bytes(candidates[0].text, 200)
}

function findHref(selectors) {
    for (const selector of selectors) {
        const node = document.querySelector(selector)
        const href = String(node?.href || node?.getAttribute('href') || '').trim()
        if (href) return href
    }
    return ''
}

function detectPageType(url) {
    const base = String(url || '').toLowerCase()
    if (base.includes('/item')) {
        return 'produto'
    }
    if (base.includes('/personal')) {
        return 'vendedor'
    }
    return 'desconhecido'
}

function parseSrcsetUrl(value) {
    const entries = String(value || '')
        .split(',')
        .map((entry) => entry.trim())
        .filter(Boolean)

    for (const entry of entries) {
        const url = entry.split(/\s+/)[0]
        if (url) return url
    }

    return ''
}

function normalizeImageCandidate(url) {
    const raw = String(url || '').trim()
    if (!raw || /^data:image\//i.test(raw)) return ''

    try {
        return new URL(raw, window.location.href).href
    } catch {
        return raw
    }
}

function readImageFromImgNode(imgNode) {
    if (!imgNode || !(imgNode instanceof HTMLImageElement)) return ''

    const src = normalizeImageCandidate(
        imgNode.currentSrc
        || imgNode.src
        || imgNode.getAttribute('data-src')
        || imgNode.getAttribute('data-lazy-src')
        || parseSrcsetUrl(imgNode.getAttribute('srcset')),
    )

    if (src) return src

    const pictureSource = imgNode.closest('picture')?.querySelector('source[srcset]')
    return normalizeImageCandidate(parseSrcsetUrl(pictureSource?.getAttribute('srcset')))
}

function readImageFromNode(node) {
    if (!node) return ''

    if (node instanceof HTMLImageElement) {
        const directSrc = readImageFromImgNode(node)
        if (directSrc) return directSrc
    }

    const imgNodes = node.querySelectorAll('img')
    for (const imgNode of imgNodes) {
        const src = readImageFromImgNode(imgNode)
        if (src) return src
    }

    const bgSource = String(
        node.style?.backgroundImage ||
        window.getComputedStyle(node).backgroundImage ||
        '',
    )
    const bgMatch = bgSource.match(/url\(["']?(.*?)["']?\)/i)
    const bgUrl = normalizeImageCandidate(bgMatch?.[1])
    if (bgUrl) return bgUrl

    const bgNodes = node.querySelectorAll('[style*="background-image"]')
    for (const bgNode of bgNodes) {
        const inlineBg = String(bgNode.getAttribute('style') || '')
        const inlineBgMatch = inlineBg.match(/background-image\s*:\s*url\(["']?(.*?)["']?\)/i)
        const inlineBgUrl = normalizeImageCandidate(inlineBgMatch?.[1])
        if (inlineBgUrl) return inlineBgUrl
    }

    return ''
}

function isNodeInViewport(node) {
    if (!node || !(node instanceof Element)) return false
    const rect = node.getBoundingClientRect()
    const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0
    return rect.bottom >= 0 && rect.top <= viewportHeight
}

function isActiveCarouselNode(node) {
    if (!node || !(node instanceof Element)) return false

    const className = String(node.className || '')
    const ariaCurrent = String(node.getAttribute('aria-current') || '').toLowerCase()
    const ariaSelected = String(node.getAttribute('aria-selected') || '').toLowerCase()

    if (ariaCurrent === 'true' || ariaSelected === 'true') return true
    return /(active|current|selected|swiper-slide-active|slick-active)/i.test(className)
}

function registerImageCandidate(bestByUrl, url, score) {
    if (!url) return

    const previous = bestByUrl.get(url)
    if (!previous || score > previous.score) {
        bestByUrl.set(url, { url, score })
    }
}

function scoreImageNode(imgNode, selectorIndex, nodeIndex, imageIndex) {
    const rect = imgNode.getBoundingClientRect()
    const area = Math.max(0, rect.width) * Math.max(0, rect.height)

    let score = 240 - (selectorIndex * 11) - nodeIndex - imageIndex

    if (isVisibleElement(imgNode)) score += 80
    if (isNodeInViewport(imgNode)) score += 45
    if (imgNode.closest('[aria-current="true"], [aria-selected="true"], [class*="active"], [class*="current"], [class*="selected"]')) {
        score += 130
    }
    if (isActiveCarouselNode(imgNode.parentElement)) score += 45
    if (isRecommendationContext(imgNode)) score -= 220

    if (area >= 120000) score += 150
    else if (area >= 70000) score += 95
    else if (area >= 25000) score += 45
    else if (area < 12000) score -= 160

    if (rect.width < 140 || rect.height < 140) score -= 120
    if (rect.top < -220 || rect.top > 980) score -= 40

    return score
}

function collectImageCandidatesFromNode(node, selectorIndex, nodeIndex, bestByUrl) {
    if (!(node instanceof Element)) return

    const imageNodes = node instanceof HTMLImageElement ? [node] : [...node.querySelectorAll('img')]
    const limit = Math.min(imageNodes.length, 24)

    for (let imageIndex = 0; imageIndex < limit; imageIndex += 1) {
        const imgNode = imageNodes[imageIndex]
        const imageUrl = readImageFromImgNode(imgNode)
        if (!imageUrl) continue

        const score = scoreImageNode(imgNode, selectorIndex, nodeIndex, imageIndex)
        registerImageCandidate(bestByUrl, imageUrl, score)
    }

    const bgUrl = readImageFromNode(node)
    if (bgUrl) {
        const rect = node.getBoundingClientRect()
        const areaBoost = Math.min(Math.max(0, rect.width * rect.height) / 1500, 80)
        let score = 70 - (selectorIndex * 8) - nodeIndex + areaBoost
        if (isActiveCarouselNode(node)) score += 100
        if (isVisibleElement(node)) score += 35
        if (isRecommendationContext(node)) score -= 180
        registerImageCandidate(bestByUrl, bgUrl, score)
    }
}

function extractCarouselImage() {
    const selectors = [
        'div[class*="carousel"] [aria-current="true"]',
        'div[class*="carousel"] [aria-selected="true"]',
        'div[class*="carousel"] [class*="active"]',
        '[class*="carouselItem--"]',
        'div[class*="carousel"] [class*="item"]',
        'div[class*="swiper"] [class*="slide"]',
        'div[class*="slick"] [class*="slide"]',
    ]

    const bestByUrl = new Map()

    for (let selectorIndex = 0; selectorIndex < selectors.length; selectorIndex += 1) {
        const selector = selectors[selectorIndex]
        const nodes = document.querySelectorAll(selector)

        const limit = Math.min(nodes.length, 18)
        for (let nodeIndex = 0; nodeIndex < limit; nodeIndex += 1) {
            const node = nodes[nodeIndex]
            collectImageCandidatesFromNode(node, selectorIndex, nodeIndex, bestByUrl)
        }
    }

    // Fallback: choose the most likely main product image when carousel markup changes.
    const fallbackImages = document.querySelectorAll('img[src], img[data-src], img[data-lazy-src]')
    const fallbackLimit = Math.min(fallbackImages.length, 80)
    for (let imageIndex = 0; imageIndex < fallbackLimit; imageIndex += 1) {
        const imgNode = fallbackImages[imageIndex]
        if (!(imgNode instanceof HTMLImageElement)) continue

        const imageUrl = readImageFromImgNode(imgNode)
        if (!imageUrl) continue

        const score = scoreImageNode(imgNode, selectors.length + 1, imageIndex, imageIndex)
        registerImageCandidate(bestByUrl, imageUrl, score)
    }

    const ranked = [...bestByUrl.values()].sort((a, b) => b.score - a.score)
    if (ranked.length) return ranked[0].url

    return ''
}

function extractPrice(text) {
    const match = String(text || '').replace(/\s+/g, ' ').match(/(?:\u00A5|yuan|cny|r\$|\$)\s*([\d.,]+)/i)
    return match?.[1] || ''
}

function scrapeCurrentPage() {
    const url = window.location.href
    const host = window.location.hostname.replace('www.', '')
    const pageType = detectPageType(url)

    if (pageType === 'desconhecido') {
        return {
            url,
            host,
            pageType,
        }
    }

    const bodyText = String(document.body?.innerText || '').slice(0, 70000)

    if (pageType === 'produto') {
        const title =
            findMeta('meta[property="og:title"]') ||
            findMeta('meta[name="twitter:title"]') ||
            String(document.title || '').trim()

        const imageUrl =
            extractCarouselImage() ||
            findMeta('meta[property="og:image"]') ||
            findMeta('meta[name="twitter:image"]') ||
            document.querySelector('img')?.src ||
            ''

        const price =
            findMeta('meta[property="product:price:amount"]') ||
            findMeta('meta[name="price"]') ||
            extractPrice(findText(['[class*="price"]', '[data-price]', '[class*="amount"]'])) ||
            extractPrice(bodyText)

        const safeProductName = extractProductName(title)

        return {
            url,
            host,
            pageType,
            productName: safeProductName,
            productLink: url,
            imageUrl,
            price,
        }
    }

    const storeName = findText([
        '[class*="store"]',
        '[class*="shop"]',
        '[data-store-name]',
        '[class*="seller"]',
        '[data-seller-name]',
    ])

    const vendorName = findText([
        '[class*="seller-name"]',
        '[class*="nickname"]',
        '[data-user-name]',
    ])

    const storeLink = findHref([
        'a[href*="/seller"]',
        'a[href*="/shop"]',
        'a[href*="/store"]',
        'a[href*="/user"]',
        '[class*="seller"] a[href]',
        '[class*="shop"] a[href]',
        '[data-store-link] a[href]',
    ])

    return {
        url,
        host,
        pageType,
        storeName,
        vendorName,
        storeLink,
    }
}

function createUI(isProductPage) {
    if (document.getElementById('citychina-saver-root')) return null

    const root = document.createElement('div')
    root.id = 'citychina-saver-root'

    let pesoInput = null
    let modalidadeSelect = null

    if (isProductPage) {
        const formBox = document.createElement('div')
        formBox.id = 'citychina-saver-form'

        const pesoLabel = document.createElement('label')
        pesoLabel.htmlFor = 'citychina-saver-peso'
        pesoLabel.textContent = 'Peso (g)'

        pesoInput = document.createElement('input')
        pesoInput.id = 'citychina-saver-peso'
        pesoInput.type = 'number'
        pesoInput.min = '1'
        pesoInput.step = '1'
        pesoInput.placeholder = 'Ex: 300'

        const modalidadeLabel = document.createElement('label')
        modalidadeLabel.htmlFor = 'citychina-saver-modalidade'
        modalidadeLabel.textContent = 'Modalidade'

        modalidadeSelect = document.createElement('select')
        modalidadeSelect.id = 'citychina-saver-modalidade'
        modalidadeSelect.disabled = true

        const loadingOption = document.createElement('option')
        loadingOption.value = ''
        loadingOption.textContent = 'Carregando modalidades...'
        modalidadeSelect.appendChild(loadingOption)

        formBox.appendChild(pesoLabel)
        formBox.appendChild(pesoInput)
        formBox.appendChild(modalidadeLabel)
        formBox.appendChild(modalidadeSelect)
        root.appendChild(formBox)
    }

    const button = document.createElement('button')
    button.id = 'citychina-saver-btn'
    button.type = 'button'
    button.textContent = 'Salvar no Sistema'

    const status = document.createElement('small')
    status.id = 'citychina-saver-status'
    status.textContent = ''

    root.appendChild(button)
    root.appendChild(status)
    document.body.appendChild(root)

    return { root, button, status, pesoInput, modalidadeSelect }
}

function setStatus(statusNode, message, mode = 'idle') {
    statusNode.textContent = message
    statusNode.dataset.mode = mode
}

function sendMessage(payload) {
    return new Promise((resolve, reject) => {
        chrome.runtime.sendMessage(payload, (result) => {
            if (chrome.runtime.lastError) {
                reject(new Error(chrome.runtime.lastError.message))
                return
            }
            resolve(result)
        })
    })
}

function fillModalidades(selectNode, modalidades, selectedId) {
    selectNode.innerHTML = ''

    if (!Array.isArray(modalidades) || !modalidades.length) {
        const emptyOption = document.createElement('option')
        emptyOption.value = ''
        emptyOption.textContent = 'Sem modalidades disponiveis'
        selectNode.appendChild(emptyOption)
        selectNode.disabled = true
        return
    }

    modalidades.forEach((modalidade) => {
        const option = document.createElement('option')
        option.value = String(modalidade.id_modalidade)
        option.textContent = `${modalidade.id_modalidade} - ${modalidade.nome_modalidade}`
        selectNode.appendChild(option)
    })

    const selectedValue = String(selectedId || '')
    if (selectedValue && modalidades.some((item) => String(item.id_modalidade) === selectedValue)) {
        selectNode.value = selectedValue
    }

    selectNode.disabled = false
}

async function loadProductFormData(ui) {
    if (!ui?.pesoInput || !ui?.modalidadeSelect) return

    try {
        const result = await sendMessage({ action: 'extension:get-product-form-data' })
        if (!result?.ok) {
            fillModalidades(ui.modalidadeSelect, [], null)
            setStatus(ui.status, result?.message || 'Nao foi possivel carregar modalidades.', 'error')
            return
        }

        ui.pesoInput.value = String(result?.config?.pesoDefault || 300)
        fillModalidades(
            ui.modalidadeSelect,
            result?.modalidades || [],
            result?.config?.idModalidade || null,
        )
    } catch (error) {
        fillModalidades(ui.modalidadeSelect, [], null)
        setStatus(ui.status, error.message || 'Falha ao carregar formulario.', 'error')
    }
}

function readProductOverrides(ui) {
    if (!ui?.pesoInput || !ui?.modalidadeSelect) {
        return { ok: true, overridePeso: null, overrideModalidadeId: null }
    }

    const peso = Number.parseInt(ui.pesoInput.value, 10)
    const modalidade = Number.parseInt(ui.modalidadeSelect.value, 10)

    if (!Number.isInteger(peso) || peso <= 0) {
        return { ok: false, message: 'Informe um peso valido em gramas.' }
    }

    if (!Number.isInteger(modalidade) || modalidade <= 0) {
        return { ok: false, message: 'Selecione uma modalidade valida.' }
    }

    return {
        ok: true,
        overridePeso: peso,
        overrideModalidadeId: modalidade,
    }
}

function startSaver() {
    const pageType = detectPageType(window.location.href)
    if (pageType === 'desconhecido') return

    const isProduct = pageType === 'produto'

    const ui = createUI(isProduct)
    if (!ui) return

    const { button, status } = ui

    if (isProduct) {
        void loadProductFormData(ui)
    }

    button.addEventListener('click', async () => {
        button.disabled = true
        setStatus(status, 'Salvando...', 'loading')

        const scraped = scrapeCurrentPage()
        if (isProduct) {
            if (scraped.productName) {
                const preview = String(scraped.productName).slice(0, 70)
                setStatus(status, `Salvando: ${preview}${scraped.productName.length > 70 ? '...' : ''}`, 'loading')
            }

            const overrides = readProductOverrides(ui)
            if (!overrides.ok) {
                setStatus(status, overrides.message || 'Dados invalidos no formulario.', 'error')
                button.disabled = false
                return
            }

            scraped.overridePeso = overrides.overridePeso
            scraped.overrideModalidadeId = overrides.overrideModalidadeId
        }

        try {
            const result = await sendMessage({
                action: 'extension:save-page',
                scraped,
            })

            if (result?.ok) {
                setStatus(status, result.message || 'Salvo com sucesso.', 'success')
            } else {
                setStatus(status, result?.message || 'Falha ao salvar.', 'error')
            }
        } catch {
            setStatus(status, 'Erro ao falar com a extensao.', 'error')
        }

        button.disabled = false
    })
}

startSaver()
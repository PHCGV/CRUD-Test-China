import { useCallback, useEffect, useMemo, useState } from 'react'
import './App.css'
import FreteServiceSelector from './components/FreteServiceSelector'

const currency = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})

const FILTERS = [
  { id: 'all', label: 'Todos' },
  { id: 'cheap', label: 'Ate R$ 50' },
  { id: 'medium', label: 'R$ 50 - R$ 150' },
  { id: 'premium', label: 'Acima de R$ 150' },
  { id: 'light', label: 'Leves (<= 500g)' },
  { id: 'heavy', label: 'Pesados (> 500g)' },
]

const FRETE_SERVICE_FILTERS = [
  { id: 'all', label: 'Todos os servicos' },
  { id: 'cssbuy', label: 'Cssbuy' },
  { id: 'hoobuy', label: 'Hoobuy' },
  { id: 'acbuy', label: 'Acbuy' },
]

const SCREENS = [
  { id: 'produtos', label: 'Produtos' },
  { id: 'fretes', label: 'Fretes' },
  { id: 'vendedores', label: 'Vendedores' },
  { id: 'cadastro', label: 'Cadastro' },
]

const PRODUCT_IMAGE_PREFIX = 'https://img.alicdn.com/bao/uploaded/'
const EXTENSION_ID = String(import.meta.env.VITE_CITYCHINA_EXTENSION_ID || '').trim()

function safeText(value, fallback = 'Nao informado') {
  if (value === null || value === undefined) return fallback
  const text = String(value).trim()
  return text.length ? text : fallback
}

function parseApiError(data) {
  if (!data) return 'Nao foi possivel concluir a operacao.'
  if (typeof data.detail === 'string') return data.detail
  if (Array.isArray(data.detail) && data.detail.length) {
    const first = data.detail[0]
    if (typeof first?.msg === 'string') return first.msg
  }
  return 'Nao foi possivel concluir a operacao.'
}

function extractSeller(link) {
  try {
    const url = new URL(link)
    const host = url.hostname.replace('www.', '')
    return host.split('.')[0] || 'Vendedor externo'
  } catch {
    return 'Vendedor externo'
  }
}

function formatFreteName(frete) {
  const nome = safeText(frete?.nome, 'Frete sem nome')
  const servico = safeText(frete?.servico, '').trim()
  return servico ? `${nome} - ${servico}` : nome
}

function normalizeFreteService(value) {
  return String(value || '').trim().toLowerCase()
}

function getPasswordStrength(password) {
  let score = 0
  if (password.length >= 8) score += 1
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score += 1
  if (/\d/.test(password)) score += 1
  if (/[^\w\s]/.test(password)) score += 1

  if (score <= 1) return { label: 'Fraca', level: 'weak' }
  if (score <= 3) return { label: 'Media', level: 'medium' }
  return { label: 'Forte', level: 'strong' }
}

function readResetTokenFromLocation() {
  const url = new URL(window.location.href)
  return (url.searchParams.get('token') || url.searchParams.get('reset_token') || '').trim()
}

function clearResetTokenFromLocation() {
  const url = new URL(window.location.href)
  url.searchParams.delete('token')
  url.searchParams.delete('reset_token')

  const nextPath = url.pathname === '/reset-password' ? '/' : url.pathname
  const query = url.searchParams.toString()
  const nextUrl = `${nextPath}${query ? `?${query}` : ''}${url.hash}`
  window.history.replaceState({}, '', nextUrl)
}

function sendMessageToExtension(extensionId, payload) {
  return new Promise((resolve, reject) => {
    if (!window.chrome?.runtime?.sendMessage) {
      reject(new Error('Chrome Runtime indisponivel no navegador atual.'))
      return
    }

    window.chrome.runtime.sendMessage(extensionId, payload, (response) => {
      const runtimeError = window.chrome?.runtime?.lastError
      if (runtimeError) {
        reject(new Error(runtimeError.message || 'Falha ao enviar mensagem para a extensao.'))
        return
      }

      resolve(response)
    })
  })
}

function App() {
  const [produtos, setProdutos] = useState([])
  const [fretes, setFretes] = useState([])
  const [modalidades, setModalidades] = useState([])
  const [vendedores, setVendedores] = useState([])
  const [filtro, setFiltro] = useState('all')
  const [freteServiceFilter, setFreteServiceFilter] = useState('all')
  const [termo, setTermo] = useState('')
  const [cotacao, setCotacao] = useState(1.2)
  const [loading, setLoading] = useState(false)
  const [globalError, setGlobalError] = useState('')
  const [refreshSeed, setRefreshSeed] = useState(0)

  const [token, setToken] = useState(() => sessionStorage.getItem('auth_token') || '')
  const [currentUser, setCurrentUser] = useState(null)
  const [activeScreen, setActiveScreen] = useState('produtos')
  const [authStatus, setAuthStatus] = useState('')
  const [authOpen, setAuthOpen] = useState(false)
  const [authTab, setAuthTab] = useState('login')
  const [failedLogins, setFailedLogins] = useState(0)
  const [lockedUntil, setLockedUntil] = useState(0)

  const [loginForm, setLoginForm] = useState({ username: '', senha: '' })
  const [registerForm, setRegisterForm] = useState({
    nome: '',
    email: '',
    username: '',
    senha: '',
    senha2: '',
  })
  const [loginError, setLoginError] = useState('')
  const [registerError, setRegisterError] = useState('')
  const [passwordForm, setPasswordForm] = useState({
    senhaAtual: '',
    novaSenha: '',
    novaSenha2: '',
  })
  const [forgotForm, setForgotForm] = useState({ email: '' })
  const [resetForm, setResetForm] = useState({
    token: '',
    novaSenha: '',
    novaSenha2: '',
  })
  const [passwordError, setPasswordError] = useState('')
  const [forgotError, setForgotError] = useState('')
  const [forgotMessage, setForgotMessage] = useState('')
  const [resetError, setResetError] = useState('')
  const [resetMessage, setResetMessage] = useState('')
  const [registering, setRegistering] = useState(false)
  const [loggingIn, setLoggingIn] = useState(false)
  const [syncingExtension, setSyncingExtension] = useState(false)
  const [changingPassword, setChangingPassword] = useState(false)
  const [requestingReset, setRequestingReset] = useState(false)
  const [resettingPassword, setResettingPassword] = useState(false)
  const [vendedorForm, setVendedorForm] = useState({
    nome: '',
    loja: '',
    link_loja: '',
  })
  const [produtoForm, setProdutoForm] = useState({
    nome: '',
    link_produto: '',
    link_imagem: '',
    valor: '',
    peso: '',
    id_modalidade: '',
    id_vendedor: '',
  })
  const [vendedorError, setVendedorError] = useState('')
  const [vendedorMessage, setVendedorMessage] = useState('')
  const [editVendedorId, setEditVendedorId] = useState(null)
  const [editVendedorForm, setEditVendedorForm] = useState({
    nome: '',
    loja: '',
    link_loja: '',
  })
  const [editVendedorError, setEditVendedorError] = useState('')
  const [editVendedorMessage, setEditVendedorMessage] = useState('')
  const [produtoError, setProdutoError] = useState('')
  const [produtoMessage, setProdutoMessage] = useState('')
  const [creatingVendedor, setCreatingVendedor] = useState(false)
  const [updatingVendedor, setUpdatingVendedor] = useState(false)
  const [creatingProduto, setCreatingProduto] = useState(false)
  const [deletingVendedorId, setDeletingVendedorId] = useState(null)
  const [editProdutoId, setEditProdutoId] = useState(null)
  const [editProdutoForm, setEditProdutoForm] = useState({
    nome: '',
    link_produto: '',
    link_imagem: '',
    valor: '',
    peso: '',
    id_modalidade: '',
    id_vendedor: '',
  })
  const [editProdutoError, setEditProdutoError] = useState('')
  const [editProdutoMessage, setEditProdutoMessage] = useState('')
  const [updatingProduto, setUpdatingProduto] = useState(false)
  const [deletingProdutoId, setDeletingProdutoId] = useState(null)
  const [freteForm, setFreteForm] = useState({
    nome: '',
    servico: '',
    valor_100g: '',
    valor_100g_plus: '',
    modalidades_ids: [],
  })
  const [freteError, setFreteError] = useState('')
  const [freteMessage, setFreteMessage] = useState('')
  const [creatingFrete, setCreatingFrete] = useState(false)
  const [simulacaoProdutoId, setSimulacaoProdutoId] = useState('')
  const [simulacaoResultado, setSimulacaoResultado] = useState(null)
  const [simulacaoError, setSimulacaoError] = useState('')
  const [simulandoFrete, setSimulandoFrete] = useState(false)
  const [ultimoVendedorAcessadoId, setUltimoVendedorAcessadoId] = useState(null)

  const getUltimoVendedorStorageKey = useCallback(() => {
    const idUsuario = currentUser?.id_usuario
    return idUsuario ? 'ultimo_vendedor_acessado:' + idUsuario : null
  }, [currentUser?.id_usuario])

  function persistToken(value) {
    setToken(value)
    sessionStorage.setItem('auth_token', value)
  }

  const clearAuth = useCallback((statusMessage = '') => {
    setToken('')
    setCurrentUser(null)
    sessionStorage.removeItem('auth_token')
    if (statusMessage) setAuthStatus(statusMessage)
  }, [])

  const apiFetch = useCallback(async (url, options = {}) => {
    const headers = { ...(options.headers || {}) }
    if (token) headers.Authorization = `Bearer ${token}`

    const response = await fetch(url, {
      ...options,
      headers,
    })

    if (response.status === 401) {
      clearAuth('Sessao expirada. Entre novamente.')
      throw new Error('Nao autorizado')
    }

    return response
  }, [clearAuth, token])

  const loadCurrentUser = useCallback(async (activeToken = token) => {
    if (!activeToken) {
      setCurrentUser(null)
      return false
    }

    const response = await fetch('/auth/me', {
      headers: {
        Authorization: `Bearer ${activeToken}`,
      },
    })

    if (!response.ok) {
      clearAuth('Sessao invalida. Entre novamente.')
      return false
    }

    const me = await response.json()
    setCurrentUser(me)
    return true
  }, [clearAuth, token])

  useEffect(() => {
    const storageKey = getUltimoVendedorStorageKey()
    if (!storageKey) {
      setUltimoVendedorAcessadoId(null)
      return
    }

    try {
      const idVendedor = Number(localStorage.getItem(storageKey))
      setUltimoVendedorAcessadoId(Number.isInteger(idVendedor) && idVendedor > 0 ? idVendedor : null)
    } catch {
      setUltimoVendedorAcessadoId(null)
    }
  }, [getUltimoVendedorStorageKey])

  function estimateFreight(produto) {
    if (!fretes.length) {
      return { valor: 0, metodo: 'Sem dados de frete' }
    }

    const peso = Number(produto.peso) || 0
    const taxa = Number(cotacao) || 1

    const options = fretes
      .map((frete) => {
        const base = Number(frete.valor_100g) / taxa
        const extra = Number(frete.valor_100g_plus) / taxa
        const extraPeso = Math.max(0, peso - 100)
        const blocos = Math.ceil(extraPeso / 100)
        const total = base + extra * blocos

        return {
          nome: formatFreteName(frete),
          total,
        }
      })
      .sort((a, b) => a.total - b.total)

    return {
      valor: options[0].total,
      metodo: options[0].nome,
    }
  }

  const getPriceBRL = useCallback((produto) => {
    const converted = Number(produto.valor_convertido)
    if (Number.isFinite(converted) && converted > 0) return converted
    return Number(produto.valor) / (Number(cotacao) || 1)
  }, [cotacao])

  const visibleProducts = useMemo(() => {
    return produtos.filter((produto) => {
      const vendedor = safeText(produto.nome_vendedor, '') || extractSeller(produto.link_produto)
      const preco = getPriceBRL(produto)
      const peso = Number(produto.peso) || 0

      let byFilter = true
      if (filtro === 'cheap') byFilter = preco <= 50
      if (filtro === 'medium') byFilter = preco > 50 && preco <= 150
      if (filtro === 'premium') byFilter = preco > 150
      if (filtro === 'light') byFilter = peso <= 500
      if (filtro === 'heavy') byFilter = peso > 500

      const q = termo.trim().toLowerCase()
      if (!q) return byFilter

      const nome = safeText(produto.nome, '').toLowerCase()
      return byFilter && (nome.includes(q) || vendedor.toLowerCase().includes(q))
    })
  }, [filtro, getPriceBRL, produtos, termo])

  const visibleVendedores = useMemo(() => {
    const q = termo.trim().toLowerCase()
    if (!q) return vendedores

    return vendedores.filter((vendedor) => {
      const nome = safeText(vendedor.nome, '').toLowerCase()
      const loja = safeText(vendedor.loja, '').toLowerCase()
      return nome.includes(q) || loja.includes(q)
    })
  }, [termo, vendedores])

  const visibleFretes = useMemo(() => {
    const q = termo.trim().toLowerCase()
    return fretes.filter((frete) => {
      const byService = freteServiceFilter === 'all'
        || normalizeFreteService(frete.servico) === freteServiceFilter

      if (!byService) return false

      if (!q) return true

      const nome = safeText(frete.nome, '').toLowerCase()
      const servico = safeText(frete.servico, '').toLowerCase()
      const modalidadesTexto = Array.isArray(frete.modalidades)
        ? frete.modalidades.join(' ').toLowerCase()
        : ''

      return nome.includes(q) || servico.includes(q) || modalidadesTexto.includes(q)
    })
  }, [fretes, termo, freteServiceFilter])

  const visibleSimulacaoOptions = useMemo(() => {
    const opcoes = Array.isArray(simulacaoResultado?.opcoes_envio)
      ? simulacaoResultado.opcoes_envio
      : []

    if (freteServiceFilter === 'all') return opcoes

    return opcoes.filter((opcao) => {
      const servico = normalizeFreteService(opcao?.Servico)
      if (servico) return servico === freteServiceFilter

      const metodo = normalizeFreteService(opcao?.['Metodo de envio'])
      return metodo.includes(freteServiceFilter)
    })
  }, [simulacaoResultado, freteServiceFilter])

  const totalVendedores = useMemo(() => {
    return vendedores.length
  }, [vendedores])

  const totalFretes = useMemo(() => {
    return fretes.length
  }, [fretes])

  useEffect(() => {
    let active = true

    async function loadData() {
      if (!token) {
        if (!active) return
        setProdutos([])
        setFretes([])
        setModalidades([])
        setVendedores([])
        setLoading(false)
        return
      }

      setLoading(true)
      setGlobalError('')

      try {
        const userOk = await loadCurrentUser(token)
        if (!userOk || !active) return

        const [prodResp, freteResp, modalidadeResp, vendedorResp] = await Promise.all([
          apiFetch(`/produto/?cotacao=${Number(cotacao) || 1.2}`),
          apiFetch('/frete/'),
          apiFetch('/modalidade/'),
          apiFetch('/vendedor/'),
        ])

        if (!prodResp.ok) {
          throw new Error('Falha ao carregar produtos')
        }

        const productList = await prodResp.json()
        const freightList = freteResp.ok ? await freteResp.json() : []
        const modalidadeList = modalidadeResp.ok ? await modalidadeResp.json() : []
        const vendedorList = vendedorResp.ok ? await vendedorResp.json() : []

        if (!active) return
        setProdutos(productList)
        setFretes(freightList)
        setModalidades(modalidadeList)
        setVendedores(vendedorList)
      } catch {
        if (!active) return
        setProdutos([])
        setFretes([])
        setModalidades([])
        setVendedores([])
        setGlobalError('Erro ao carregar dados da API. Verifique se o backend esta ativo.')
      } finally {
        if (active) setLoading(false)
      }
    }

    void loadData()

    return () => {
      active = false
    }
  }, [refreshSeed, token, cotacao, apiFetch, loadCurrentUser])

  useEffect(() => {
    if (!authStatus) return

    const id = window.setTimeout(() => {
      setAuthStatus('')
    }, 3500)

    return () => window.clearTimeout(id)
  }, [authStatus])

  useEffect(() => {
    const tokenFromUrl = readResetTokenFromLocation()
    if (!tokenFromUrl) return

    setResetForm((prev) => ({ ...prev, token: tokenFromUrl }))
    setAuthTab('reset')
    setAuthOpen(true)
  }, [])

  async function onRegister(event) {
    event.preventDefault()
    setRegisterError('')

    const nome = registerForm.nome.trim()
    const email = registerForm.email.trim().toLowerCase()
    const username = registerForm.username.trim()
    const senha = registerForm.senha
    const senha2 = registerForm.senha2

    if (!nome || !username || !senha || !senha2) {
      setRegisterError('Preencha todos os campos.')
      return
    }

    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setRegisterError('Informe um e-mail valido.')
      return
    }

    if (getPasswordStrength(senha).level === 'weak') {
      setRegisterError('Use uma senha mais forte com letras, numeros e simbolos.')
      return
    }

    if (senha !== senha2) {
      setRegisterError('As senhas nao conferem.')
      return
    }

    setRegistering(true)
    try {
      const response = await fetch('/auth/registrar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nome, username, senha, email: email || null }),
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        setRegisterError(parseApiError(data))
        return
      }

      setAuthStatus('Conta criada. Entre para continuar.')
      setAuthTab('login')
      setLoginForm((prev) => ({ ...prev, username, senha: '' }))
      setRegisterForm({ nome: '', email: '', username: '', senha: '', senha2: '' })
    } finally {
      setRegistering(false)
    }
  }

  async function onCreateVendedor(event) {
    event.preventDefault()
    setVendedorError('')
    setVendedorMessage('')

    const nome = vendedorForm.nome.trim()
    const loja = vendedorForm.loja.trim()
    const linkLoja = vendedorForm.link_loja.trim()

    if (!nome || !loja) {
      setVendedorError('Informe nome e loja do vendedor.')
      return
    }

    if (linkLoja && !/^https?:\/\//i.test(linkLoja)) {
      setVendedorError('O link da loja deve iniciar com http:// ou https://')
      return
    }

    setCreatingVendedor(true)
    try {
      const response = await apiFetch('/vendedor/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nome,
          loja,
          link_loja: linkLoja || null,
        }),
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        setVendedorError(parseApiError(data))
        return
      }

      setVendedorForm({ nome: '', loja: '', link_loja: '' })
      setVendedorMessage('Vendedor adicionado com sucesso.')
      setEditVendedorMessage('')
      setRefreshSeed((seed) => seed + 1)
    } finally {
      setCreatingVendedor(false)
    }
  }

  function onStartEditVendedor(vendedor) {
    setEditVendedorId(vendedor.id_vendedor)
    setEditVendedorError('')
    setEditVendedorMessage('')
    setEditVendedorForm({
      nome: String(vendedor.nome || ''),
      loja: String(vendedor.loja || ''),
      link_loja: String(vendedor.link_loja || ''),
    })
  }

  function onCancelEditVendedor() {
    setEditVendedorId(null)
    setEditVendedorError('')
    setEditVendedorForm({ nome: '', loja: '', link_loja: '' })
  }

  async function onUpdateVendedor(event, idVendedor) {
    event.preventDefault()
    setEditVendedorError('')
    setEditVendedorMessage('')

    const nome = editVendedorForm.nome.trim()
    const loja = editVendedorForm.loja.trim()
    const vendedorAtual = vendedores.find((item) => item.id_vendedor === idVendedor)
    const linkLoja = String(vendedorAtual?.link_loja || '').trim()

    if (!nome || !loja) {
      setEditVendedorError('Informe nome e loja do vendedor.')
      return
    }

    setUpdatingVendedor(true)
    try {
      const response = await apiFetch(`/vendedor/${idVendedor}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nome,
          loja,
          link_loja: linkLoja || null,
        }),
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        setEditVendedorError(parseApiError(data))
        return
      }

      setEditVendedorId(null)
      setEditVendedorForm({ nome: '', loja: '', link_loja: '' })
      setEditVendedorMessage('Vendedor atualizado com sucesso.')
      setRefreshSeed((seed) => seed + 1)
    } finally {
      setUpdatingVendedor(false)
    }
  }

  async function onDeleteVendedor(vendedor) {
    const idVendedor = vendedor.id_vendedor
    const confirmado = window.confirm(`Remover o vendedor ${safeText(vendedor.nome)}?`)
    if (!confirmado) return

    setEditVendedorError('')
    setEditVendedorMessage('')
    setDeletingVendedorId(idVendedor)
    try {
      const response = await apiFetch(`/vendedor/${idVendedor}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        setEditVendedorError(parseApiError(data))
        return
      }

      if (editVendedorId === idVendedor) {
        onCancelEditVendedor()
      }
      if (ultimoVendedorAcessadoId === idVendedor) {
        const storageKey = getUltimoVendedorStorageKey()
        setUltimoVendedorAcessadoId(null)
        try {
          if (storageKey) localStorage.removeItem(storageKey)
        } catch {
          // Vendor deletion does not depend on local storage.
        }
      }
      setEditVendedorMessage('Vendedor removido com sucesso.')
      setRefreshSeed((seed) => seed + 1)
    } finally {
      setDeletingVendedorId(null)
    }
  }

  function onOpenVendedor(vendedor) {
    const idVendedor = vendedor.id_vendedor
    const storageKey = getUltimoVendedorStorageKey()

    setUltimoVendedorAcessadoId(idVendedor)
    try {
      if (storageKey) localStorage.setItem(storageKey, String(idVendedor))
    } catch {
      // A abertura da loja continua disponível caso o navegador bloqueie o armazenamento local.
    }

    window.open(vendedor.link_loja, 'blank', 'noopener')
  }

  async function onCreateProduto(event) {
    event.preventDefault()
    setProdutoError('')
    setProdutoMessage('')

    const nome = produtoForm.nome.trim()
    const linkProduto = produtoForm.link_produto.trim()
    const linkImagem = produtoForm.link_imagem.trim()
    const valor = Number(produtoForm.valor)
    const peso = Number(produtoForm.peso)
    const idModalidade = Number(produtoForm.id_modalidade)
    const idVendedor = produtoForm.id_vendedor ? Number(produtoForm.id_vendedor) : null

    if (!nome || !linkProduto || !produtoForm.valor || !produtoForm.peso || !produtoForm.id_modalidade) {
      setProdutoError('Preencha nome, link do produto, valor, peso e modalidade.')
      return
    }

    if (!/^https?:\/\//i.test(linkProduto)) {
      setProdutoError('O link do produto deve iniciar com http:// ou https://')
      return
    }

    if (linkImagem && !/^https?:\/\//i.test(linkImagem)) {
      setProdutoError('O link da imagem deve iniciar com http:// ou https://')
      return
    }

    if (linkImagem && !linkImagem.startsWith(PRODUCT_IMAGE_PREFIX)) {
      setProdutoError(`O link da imagem deve iniciar com ${PRODUCT_IMAGE_PREFIX}`)
      return
    }

    if (!Number.isFinite(valor) || valor <= 0) {
      setProdutoError('Informe um valor valido para o produto.')
      return
    }

    if (!Number.isFinite(peso) || peso <= 0) {
      setProdutoError('Informe um peso valido em gramas.')
      return
    }

    if (!Number.isInteger(idModalidade) || idModalidade <= 0) {
      setProdutoError('Informe um ID de modalidade valido.')
      return
    }

    if (idVendedor !== null && (!Number.isInteger(idVendedor) || idVendedor <= 0)) {
      setProdutoError('Vendedor selecionado invalido.')
      return
    }

    setCreatingProduto(true)
    try {
      const response = await apiFetch('/produto/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nome,
          link_produto: linkProduto,
          link_imagem: linkImagem || null,
          valor,
          peso,
          id_modalidade: idModalidade,
          id_vendedor: idVendedor,
        }),
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        setProdutoError(parseApiError(data))
        return
      }

      setProdutoForm({
        nome: '',
        link_produto: '',
        link_imagem: '',
        valor: '',
        peso: '',
        id_modalidade: '',
        id_vendedor: '',
      })
      setProdutoMessage('Produto adicionado com sucesso.')
      setRefreshSeed((seed) => seed + 1)
    } finally {
      setCreatingProduto(false)
    }
  }

  function onToggleFreteModalidade(idModalidade) {
    setFreteForm((prev) => {
      const current = Array.isArray(prev.modalidades_ids) ? prev.modalidades_ids : []
      const exists = current.includes(idModalidade)
      const modalidades_ids = exists
        ? current.filter((id) => id !== idModalidade)
        : [...current, idModalidade]

      return { ...prev, modalidades_ids }
    })
  }

  async function onCreateFrete(event) {
    event.preventDefault()
    setFreteError('')
    setFreteMessage('')

    if (currentUser?.perfil !== 'ADMIN') {
      setFreteError('Apenas usuarios ADMIN podem cadastrar fretes.')
      return
    }

    const nome = freteForm.nome.trim()
    const servico = freteForm.servico.trim()
    const valor100g = Number(freteForm.valor_100g)
    const valor100gPlus = Number(freteForm.valor_100g_plus)
    const modalidadesIds = Array.isArray(freteForm.modalidades_ids)
      ? freteForm.modalidades_ids.filter((id) => Number.isInteger(id) && id > 0)
      : []

    if (!nome || !servico || !freteForm.valor_100g || !freteForm.valor_100g_plus) {
      setFreteError('Preencha nome, servico, valor 100g e valor adicional.')
      return
    }

    if (!Number.isFinite(valor100g) || valor100g <= 0) {
      setFreteError('Informe um valor valido para 100g.')
      return
    }

    if (!Number.isFinite(valor100gPlus) || valor100gPlus <= 0) {
      setFreteError('Informe um valor valido para cada 100g adicional.')
      return
    }

    if (!modalidadesIds.length) {
      setFreteError('Selecione ao menos uma modalidade para o frete.')
      return
    }

    setCreatingFrete(true)
    try {
      const response = await apiFetch('/frete/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nome,
          servico,
          valor_100g: valor100g,
          valor_100g_plus: valor100gPlus,
          modalidades_ids: modalidadesIds,
        }),
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        setFreteError(parseApiError(data))
        return
      }

      setFreteForm({
        nome: '',
        servico: '',
        valor_100g: '',
        valor_100g_plus: '',
        modalidades_ids: [],
      })
      setFreteMessage('Frete adicionado com sucesso.')
      setRefreshSeed((seed) => seed + 1)
    } finally {
      setCreatingFrete(false)
    }
  }

  async function onSimularFrete(event) {
    event.preventDefault()
    setSimulacaoError('')
    setSimulacaoResultado(null)

    const idProduto = Number(simulacaoProdutoId)
    if (!Number.isInteger(idProduto) || idProduto <= 0) {
      setSimulacaoError('Selecione um produto valido para simular.')
      return
    }

    setSimulandoFrete(true)
    try {
      const response = await apiFetch(`/simularcusto/${idProduto}?cotacao=${Number(cotacao) || 1.2}`)
      const data = await response.json().catch(() => ({}))

      if (!response.ok) {
        setSimulacaoError(parseApiError(data))
        return
      }

      setSimulacaoResultado(data)
    } finally {
      setSimulandoFrete(false)
    }
  }

  function onStartEditProduto(produto) {
    setEditProdutoId(produto.id_produto)
    setEditProdutoError('')
    setEditProdutoMessage('')
    setEditProdutoForm({
      nome: String(produto.nome || ''),
      link_produto: String(produto.link_produto || ''),
      link_imagem: String(produto.link_imagem || ''),
      valor: String(produto.valor || ''),
      peso: String(produto.peso || ''),
      id_modalidade: String(produto.id_modalidade || ''),
      id_vendedor: produto.id_vendedor ? String(produto.id_vendedor) : '',
    })
  }

  function onCancelEditProduto() {
    setEditProdutoId(null)
    setEditProdutoError('')
    setEditProdutoForm({
      nome: '',
      link_produto: '',
      link_imagem: '',
      valor: '',
      peso: '',
      id_modalidade: '',
      id_vendedor: '',
    })
  }

  async function onUpdateProduto(event, idProduto) {
    event.preventDefault()
    setEditProdutoError('')
    setEditProdutoMessage('')

    const nome = editProdutoForm.nome.trim()
    const linkImagem = editProdutoForm.link_imagem.trim()
    const valor = Number(editProdutoForm.valor)
    const peso = Number(editProdutoForm.peso)
    const idModalidade = Number(editProdutoForm.id_modalidade)
    const idVendedor = editProdutoForm.id_vendedor ? Number(editProdutoForm.id_vendedor) : null

    if (!nome || !editProdutoForm.valor || !editProdutoForm.peso || !editProdutoForm.id_modalidade) {
      setEditProdutoError('Preencha nome, valor, peso e modalidade.')
      return
    }

    if (!Number.isFinite(valor) || valor <= 0) {
      setEditProdutoError('Informe um valor valido para o produto.')
      return
    }

    if (!Number.isFinite(peso) || peso <= 0) {
      setEditProdutoError('Informe um peso valido em gramas.')
      return
    }

    if (!Number.isInteger(idModalidade) || idModalidade <= 0) {
      setEditProdutoError('Informe um ID de modalidade valido.')
      return
    }

    if (idVendedor !== null && (!Number.isInteger(idVendedor) || idVendedor <= 0)) {
      setEditProdutoError('Vendedor selecionado invalido.')
      return
    }

    if (linkImagem && !/^https?:\/\//i.test(linkImagem)) {
      setEditProdutoError('O link da imagem deve iniciar com http:// ou https://')
      return
    }

    if (linkImagem && !linkImagem.startsWith(PRODUCT_IMAGE_PREFIX)) {
      setEditProdutoError(`O link da imagem deve iniciar com ${PRODUCT_IMAGE_PREFIX}`)
      return
    }

    setUpdatingProduto(true)
    try {
      const response = await apiFetch(`/produto/${idProduto}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nome,
          link_imagem: linkImagem || null,
          valor,
          peso,
          id_modalidade: idModalidade,
          id_vendedor: idVendedor,
        }),
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        setEditProdutoError(parseApiError(data))
        return
      }

      onCancelEditProduto()
      setEditProdutoMessage('Produto atualizado com sucesso.')
      setRefreshSeed((seed) => seed + 1)
    } finally {
      setUpdatingProduto(false)
    }
  }

  async function onDeleteProduto(produto) {
    const idProduto = produto.id_produto
    const confirmado = window.confirm(`Remover o produto ${safeText(produto.nome)}?`)
    if (!confirmado) return

    setEditProdutoError('')
    setEditProdutoMessage('')
    setDeletingProdutoId(idProduto)
    try {
      const response = await apiFetch(`/produto/${idProduto}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        setEditProdutoError(parseApiError(data))
        return
      }

      if (editProdutoId === idProduto) {
        onCancelEditProduto()
      }
      setEditProdutoMessage('Produto removido com sucesso.')
      setRefreshSeed((seed) => seed + 1)
    } finally {
      setDeletingProdutoId(null)
    }
  }

  function isLoginLocked() {
    if (Date.now() >= lockedUntil) return false
    const seconds = Math.ceil((lockedUntil - Date.now()) / 1000)
    setAuthStatus(`Login bloqueado por ${seconds}s.`)
    return true
  }

  async function onLogin(event) {
    event.preventDefault()
    if (isLoginLocked()) return

    const username = loginForm.username.trim()
    const senha = loginForm.senha

    setLoginError('')

    if (!username || !senha) {
      setLoginError('Informe username e senha.')
      return
    }

    setLoggingIn(true)
    try {
      const response = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, senha }),
      })

      if (!response.ok) {
        const nextFails = failedLogins + 1
        setFailedLogins(nextFails)
        if (nextFails >= 3) {
          setLockedUntil(Date.now() + 15000)
          setAuthStatus('Muitas tentativas. Aguarde 15s.')
        }
        setLoginError('Falha no login. Verifique as credenciais.')
        return
      }

      const data = await response.json()
      persistToken(data.access_token)
      setFailedLogins(0)
      setLockedUntil(0)
      setLoginForm((prev) => ({ ...prev, senha: '' }))
      setAuthOpen(false)
      setAuthStatus('Login realizado com sucesso.')
      setRefreshSeed((seed) => seed + 1)
    } finally {
      setLoggingIn(false)
    }
  }

  async function onChangePassword(event) {
    event.preventDefault()

    if (!currentUser) {
      setPasswordError('Sessao invalida. Entre novamente.')
      return
    }

    const senhaAtual = passwordForm.senhaAtual
    const novaSenha = passwordForm.novaSenha
    const novaSenha2 = passwordForm.novaSenha2

    setPasswordError('')

    if (!senhaAtual || !novaSenha || !novaSenha2) {
      setPasswordError('Preencha todos os campos.')
      return
    }

    if (senhaAtual === novaSenha) {
      setPasswordError('A nova senha deve ser diferente da senha atual.')
      return
    }

    if (getPasswordStrength(novaSenha).level === 'weak') {
      setPasswordError('Use uma senha mais forte com letras, numeros e simbolos.')
      return
    }

    if (novaSenha !== novaSenha2) {
      setPasswordError('As senhas nao conferem.')
      return
    }

    setChangingPassword(true)
    try {
      const response = await apiFetch('/auth/trocar-senha', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          senha_atual: senhaAtual,
          nova_senha: novaSenha,
        }),
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        setPasswordError(parseApiError(data))
        return
      }

      setAuthOpen(false)
      setAuthTab('login')
      setPasswordForm({ senhaAtual: '', novaSenha: '', novaSenha2: '' })
      setProdutos([])
      setFretes([])
      clearAuth('Senha alterada com sucesso. Entre novamente.')
    } finally {
      setChangingPassword(false)
      setPasswordForm((prev) => ({ ...prev, senhaAtual: '' }))
    }
  }

  async function onConnectExtension() {
    if (!currentUser || !token) {
      setAuthStatus('Entre no sistema para sincronizar a extensao.')
      return
    }

    if (!EXTENSION_ID) {
      setAuthStatus('Defina VITE_CITYCHINA_EXTENSION_ID no frontend para conectar a extensao.')
      return
    }

    setSyncingExtension(true)
    try {
      const response = await apiFetch('/auth/extension-token', {
        method: 'POST',
      })
      const data = await response.json().catch(() => ({}))

      if (!response.ok || !data?.access_token) {
        setAuthStatus(parseApiError(data))
        return
      }

      const extResp = await sendMessageToExtension(EXTENSION_ID, {
        action: 'extension:sync-session',
        token: data.access_token,
        apiBase: window.location.origin,
      })

      if (!extResp?.ok) {
        setAuthStatus(extResp?.message || 'Nao foi possivel sincronizar a sessao com a extensao.')
        return
      }

      setAuthStatus('Extensao conectada com sucesso.')
    } catch (error) {
      if (error instanceof Error && error.message) {
        setAuthStatus(error.message)
        return
      }

      setAuthStatus('Nao foi possivel conectar com a extensao.')
    } finally {
      setSyncingExtension(false)
    }
  }

  async function onForgotPassword(event) {
    event.preventDefault()

    const email = forgotForm.email.trim()
    setForgotError('')
    setForgotMessage('')

    if (!email) {
      setForgotError('Informe o e-mail da conta.')
      return
    }

    setRequestingReset(true)
    try {
      const response = await fetch('/auth/esqueci-senha', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        setForgotError(parseApiError(data))
        return
      }

      const data = await response.json().catch(() => ({}))
      setForgotMessage(data.message || 'Se o e-mail estiver cadastrado, enviaremos instrucoes de recuperacao.')
    } finally {
      setRequestingReset(false)
    }
  }

  async function onResetPassword(event) {
    event.preventDefault()

    const tokenValue = resetForm.token.trim()
    const novaSenha = resetForm.novaSenha
    const novaSenha2 = resetForm.novaSenha2

    setResetError('')
    setResetMessage('')

    if (!tokenValue || !novaSenha || !novaSenha2) {
      setResetError('Preencha token, nova senha e confirmacao.')
      return
    }

    if (getPasswordStrength(novaSenha).level === 'weak') {
      setResetError('Use uma senha mais forte com letras, numeros e simbolos.')
      return
    }

    if (novaSenha !== novaSenha2) {
      setResetError('As senhas nao conferem.')
      return
    }

    setResettingPassword(true)
    try {
      const response = await fetch('/auth/redefinir-senha', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: tokenValue,
          nova_senha: novaSenha,
        }),
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        setResetError(parseApiError(data))
        return
      }

      clearResetTokenFromLocation()
      setResetForm({ token: '', novaSenha: '', novaSenha2: '' })
      setAuthTab('login')
      setLoginForm((prev) => ({ ...prev, senha: '' }))
      setResetMessage('Senha redefinida com sucesso. Faca login com a nova senha.')
      setAuthStatus('Senha redefinida com sucesso. Entre para continuar.')
    } finally {
      setResettingPassword(false)
    }
  }

  function onLogout() {
    clearAuth('Sessao encerrada.')
    setActiveScreen('produtos')
    setProdutos([])
    setFretes([])
    setModalidades([])
    setVendedores([])
    setVendedorError('')
    setVendedorMessage('')
    setEditVendedorId(null)
    setEditVendedorError('')
    setEditVendedorMessage('')
    setEditVendedorForm({ nome: '', loja: '', link_loja: '' })
    setDeletingVendedorId(null)
    setProdutoError('')
    setProdutoMessage('')
    setEditProdutoId(null)
    setEditProdutoError('')
    setEditProdutoMessage('')
    setEditProdutoForm({
      nome: '',
      link_produto: '',
      link_imagem: '',
      valor: '',
      peso: '',
      id_modalidade: '',
      id_vendedor: '',
    })
    setDeletingProdutoId(null)
    setPasswordForm({ senhaAtual: '', novaSenha: '', novaSenha2: '' })
    setPasswordError('')
    setFreteForm({
      nome: '',
      servico: '',
      valor_100g: '',
      valor_100g_plus: '',
      modalidades_ids: [],
    })
    setFreteError('')
    setFreteMessage('')
    setSimulacaoProdutoId('')
    setSimulacaoResultado(null)
    setSimulacaoError('')
    setFreteServiceFilter('all')
  }

  const strength = getPasswordStrength(registerForm.senha || '')
  const passwordStrength = getPasswordStrength(passwordForm.novaSenha || '')
  const resetStrength = getPasswordStrength(resetForm.novaSenha || '')
  const isAdmin = currentUser?.perfil === 'ADMIN'
  const searchPlaceholder = activeScreen === 'vendedores'
    ? 'Pesquisar por nome do vendedor ou loja...'
    : activeScreen === 'fretes'
      ? 'Pesquisar por nome do frete, servico ou modalidade...'
      : 'Pesquisar por nome do produto ou vendedor...'

  return (
    <>
      <div className="app-bg" />

      <header className="topbar">
        <div className="brand">
          City<span>China</span>
        </div>

        <div className="search-wrap">
          <input
            type="search"
            value={termo}
            onChange={(event) => setTermo(event.target.value)}
            placeholder={searchPlaceholder}
            disabled={token && activeScreen === 'cadastro'}
          />
          <button
            type="button"
            className="ghost-btn"
            onClick={() => setRefreshSeed((seed) => seed + 1)}
            disabled={token && activeScreen === 'cadastro'}
          >
            Atualizar
          </button>
        </div>

        <div className="quote-box">
          <label htmlFor="cotacaoInput">Cotacao ¥/R$</label>
          <input
            id="cotacaoInput"
            type="number"
            min="0.01"
            step="0.01"
            value={cotacao}
            onChange={(event) => {
              const value = Number(event.target.value)
              setCotacao(value > 0 ? value : 1.2)
            }}
          />
        </div>

        <section className="auth-box">
          {currentUser ? <span className="auth-user">{currentUser.username}</span> : null}

          {!currentUser ? (
            <button
              type="button"
              className="ghost-btn access-btn"
              onClick={() => {
                setLoginError('')
                setForgotError('')
                setResetError('')
                setAuthTab('login')
                setAuthOpen(true)
              }}
            >
              Entrar
            </button>
          ) : (
            <>
              <button
                type="button"
                className="ghost-btn"
                onClick={onConnectExtension}
                disabled={syncingExtension}
              >
                {syncingExtension ? 'Conectando extensao...' : 'Conectar extensao'}
              </button>
              <button
                type="button"
                className="ghost-btn"
                onClick={() => {
                  setPasswordError('')
                  setPasswordForm({ senhaAtual: '', novaSenha: '', novaSenha2: '' })
                  setAuthTab('password')
                  setAuthOpen(true)
                }}
              >
                Trocar senha
              </button>
              <button type="button" className="ghost-btn" onClick={onLogout}>
                Sair
              </button>
            </>
          )}

          {authStatus ? <small className="auth-status">{authStatus}</small> : null}
        </section>
      </header>

      <main className="page">
        {!token ? (
          <div className="empty-state">
            <h2>Acesso protegido</h2>
            <p>Entre para visualizar os seus produtos e vendedores.</p>
          </div>
        ) : null}

        {token && loading ? (
          <div className="empty-state">
            <h2>Carregando...</h2>
            <p>Buscando dados da sua conta.</p>
          </div>
        ) : null}

        {token && !loading && globalError ? (
          <div className="empty-state">
            <h2>Erro ao carregar</h2>
            <p>{globalError}</p>
          </div>
        ) : null}

        {token && !loading && !globalError ? (
          <>
            <section className="screen-tabs">
              {SCREENS.map((screen) => (
                <button
                  key={screen.id}
                  type="button"
                  className={`chip ${activeScreen === screen.id ? 'chip-active' : ''}`}
                  onClick={() => setActiveScreen(screen.id)}
                >
                  {screen.label}
                </button>
              ))}
            </section>

            <section className="stats">
              <div className="stat-card">
                <span>Produtos cadastrados</span>
                <strong>{produtos.length}</strong>
              </div>
              <div className="stat-card">
                <span>Fretes cadastrados</span>
                <strong>{totalFretes}</strong>
              </div>
              <div className="stat-card">
                <span>Vendedores cadastrados</span>
                <strong>{totalVendedores}</strong>
              </div>
            </section>

            {activeScreen === 'produtos' ? (
              <>
                {editProdutoMessage ? <p className="form-success">{editProdutoMessage}</p> : null}
                {editProdutoError ? <p className="form-error">{editProdutoError}</p> : null}

                <section className="toolbar">
                  {FILTERS.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      className={`chip ${item.id === filtro ? 'chip-active' : ''}`}
                      onClick={() => setFiltro(item.id)}
                    >
                      {item.label}
                    </button>
                  ))}
                </section>

                <section className="grid">
                  {visibleProducts.map((produto, index) => {
                    const vendedor = safeText(produto.nome_vendedor, '') || extractSeller(produto.link_produto)
                    const frete = estimateFreight(produto)
                    const preco = getPriceBRL(produto)

                    return (
                      <article className="product-card" key={produto.id_produto || `${produto.nome}-${index}`}>
                        <div className="image-wrap">
                          <img
                            className="product-image"
                            src={safeText(produto.link_imagem, 'https://via.placeholder.com/450x300?text=Produto')}
                            alt={safeText(produto.nome)}
                            loading="lazy"
                            onError={(event) => {
                              event.currentTarget.src = 'https://via.placeholder.com/450x300?text=Sem+imagem'
                            }}
                          />
                          <span className="seller-badge">{vendedor}</span>
                        </div>

                        {editProdutoId === produto.id_produto ? (
                          <form className="product-edit-form" onSubmit={(event) => onUpdateProduto(event, produto.id_produto)}>
                            <label htmlFor={`produtoNomeEdit-${produto.id_produto}`}>Nome</label>
                            <input
                              id={`produtoNomeEdit-${produto.id_produto}`}
                              type="text"
                              minLength={2}
                              maxLength={250}
                              value={editProdutoForm.nome}
                              onChange={(event) => setEditProdutoForm((prev) => ({ ...prev, nome: event.target.value }))}
                              required
                            />

                            <label htmlFor={`produtoLinkEdit-${produto.id_produto}`}>Link do produto (nao editavel)</label>
                            <input
                              id={`produtoLinkEdit-${produto.id_produto}`}
                              type="url"
                              value={editProdutoForm.link_produto}
                              readOnly
                            />

                            <label htmlFor={`produtoImagemEdit-${produto.id_produto}`}>Link da imagem</label>
                            <input
                              id={`produtoImagemEdit-${produto.id_produto}`}
                              type="url"
                              value={editProdutoForm.link_imagem}
                              onChange={(event) => setEditProdutoForm((prev) => ({ ...prev, link_imagem: event.target.value }))}
                              placeholder={PRODUCT_IMAGE_PREFIX}
                            />

                            <div className="manage-inline">
                              <div>
                                <label htmlFor={`produtoValorEdit-${produto.id_produto}`}>Valor (yuan)</label>
                                <input
                                  id={`produtoValorEdit-${produto.id_produto}`}
                                  type="number"
                                  min="0.01"
                                  step="0.01"
                                  value={editProdutoForm.valor}
                                  onChange={(event) => setEditProdutoForm((prev) => ({ ...prev, valor: event.target.value }))}
                                  required
                                />
                              </div>
                              <div>
                                <label htmlFor={`produtoPesoEdit-${produto.id_produto}`}>Peso (g)</label>
                                <input
                                  id={`produtoPesoEdit-${produto.id_produto}`}
                                  type="number"
                                  min="1"
                                  step="1"
                                  value={editProdutoForm.peso}
                                  onChange={(event) => setEditProdutoForm((prev) => ({ ...prev, peso: event.target.value }))}
                                  required
                                />
                              </div>
                            </div>

                            <div className="manage-inline">
                              <div>
                                <label htmlFor={`produtoModalidadeEdit-${produto.id_produto}`}>ID modalidade</label>
                                <input
                                  id={`produtoModalidadeEdit-${produto.id_produto}`}
                                  type="number"
                                  min="1"
                                  step="1"
                                  value={editProdutoForm.id_modalidade}
                                  onChange={(event) => setEditProdutoForm((prev) => ({ ...prev, id_modalidade: event.target.value }))}
                                  required
                                />
                              </div>
                              <div>
                                <label htmlFor={`produtoVendedorEdit-${produto.id_produto}`}>Vendedor (opcional)</label>
                                <select
                                  id={`produtoVendedorEdit-${produto.id_produto}`}
                                  value={editProdutoForm.id_vendedor}
                                  onChange={(event) => setEditProdutoForm((prev) => ({ ...prev, id_vendedor: event.target.value }))}
                                >
                                  <option value="">Sem vendedor</option>
                                  {vendedores.map((item) => (
                                    <option key={item.id_vendedor} value={item.id_vendedor}>
                                      {`${item.nome} (${item.loja})`}
                                    </option>
                                  ))}
                                </select>
                              </div>
                            </div>

                            <div className="product-actions">
                              <button type="submit" className="ghost-btn primary-btn" disabled={updatingProduto}>
                                {updatingProduto ? 'Salvando...' : 'Salvar'}
                              </button>
                              <button type="button" className="ghost-btn" onClick={onCancelEditProduto} disabled={updatingProduto}>
                                Cancelar
                              </button>
                            </div>
                          </form>
                        ) : (
                          <div className="card-content">
                            <h3 className="product-name">{safeText(produto.nome)}</h3>

                            <div className="price-row">
                              <div>
                                <small>Preco base</small>
                                <strong>{currency.format(Number.isFinite(preco) ? preco : 0)}</strong>
                              </div>
                              <div>
                                <small>Peso</small>
                                <strong>{`${Number(produto.peso) || 0}g`}</strong>
                              </div>
                              <div>
                                <small>Modalidade</small>
                                <strong>{`#${Number(produto.id_modalidade) || '-'}`}</strong>
                              </div>
                            </div>

                            <div className="freight-box">
                              <small>Frete estimado</small>
                              <strong>{currency.format(Number.isFinite(frete.valor) ? frete.valor : 0)}</strong>
                              <p>{`Melhor opcao: ${frete.metodo}`}</p>
                            </div>

                            <div className='freight-box'>
                              <small>Valor total: </small>
                              <strong>{currency.format(Number.isFinite(Number(frete.valor) + Number(preco)) ? 
                                (Number(frete.valor) + Number(preco)) : 0)} </strong>
                            </div>

                            <div className="product-actions">
                              <button type="button" className="ghost-btn success-btn" onClick={() => window.open(produto.link_produto, 'blank', 'noopener')}>
                              Abrir
                            </button>
                              <button type="button" className="ghost-btn" onClick={() => onStartEditProduto(produto)}>
                                Editar
                              </button>
                              <button
                                type="button"
                                className="ghost-btn danger-btn"
                                onClick={() => onDeleteProduto(produto)}
                                disabled={deletingProdutoId === produto.id_produto}
                              >
                                {deletingProdutoId === produto.id_produto ? 'Removendo...' : 'Remover'}
                              </button>
                            </div>
                          </div>
                        )}
                      </article>
                    )
                  })}
                </section>

                {!visibleProducts.length ? (
                  <div className="empty-state">
                    <h2>Nenhum item encontrado</h2>
                    <p>Ajuste os filtros ou a busca para ver outros resultados.</p>
                  </div>
                ) : null}
              </>
            ) : null}

            {activeScreen === 'fretes' ? (
              <>
                <FreteServiceSelector
                  filters={FRETE_SERVICE_FILTERS}
                  value={freteServiceFilter}
                  onChange={setFreteServiceFilter}
                />

                <section className="frete-sim-grid">
                  <form className="manage-form" onSubmit={onSimularFrete}>
                    <h3>Simular custo por produto</h3>
                    <label htmlFor="simulacaoProduto">Produto</label>
                    <select
                      id="simulacaoProduto"
                      value={simulacaoProdutoId}
                      onChange={(event) => setSimulacaoProdutoId(event.target.value)}
                      required
                    >
                      <option value="">Selecione um produto</option>
                      {produtos.map((produto) => (
                        <option key={produto.id_produto} value={produto.id_produto}>
                          {safeText(produto.nome)}
                        </option>
                      ))}
                    </select>

                    <p className="screen-note">A simulacao usa os fretes vinculados a modalidade do produto.</p>

                    {simulacaoError ? <p className="form-error">{simulacaoError}</p> : null}

                    <div className="dialog-actions">
                      <button type="submit" className="ghost-btn primary-btn" disabled={simulandoFrete}>
                        {simulandoFrete ? 'Simulando...' : 'Simular frete'}
                      </button>
                    </div>
                  </form>

                  <section className="manage-form sim-result-card" aria-live="polite">
                    <h3>Resultado da simulacao</h3>
                    {!simulacaoResultado ? (
                      <p className="screen-note">Selecione um produto e execute a simulacao para ver as opcoes.</p>
                    ) : (
                      <>
                        <p className="sim-line"><strong>Produto:</strong> {safeText(simulacaoResultado.produto)}</p>
                        <p className="sim-line"><strong>Valor:</strong> {currency.format(Number(simulacaoResultado.valor_produto) || 0)}</p>
                        <p className="sim-line"><strong>Peso:</strong> {`${Number(simulacaoResultado.peso_produto) || 0}g`}</p>

                        <div className="sim-options">
                          {visibleSimulacaoOptions.map((opcao, index) => (
                            <article className="sim-option" key={`${opcao['Metodo de envio']}-${index}`}>
                              <strong>{safeText(opcao['Metodo de envio'])}</strong>
                              <span>{currency.format(Number(opcao['Valor em Reais']) || 0)}</span>
                              <small>
                                {`Base: ${currency.format(Number(opcao?.Detalhes?.['Valor base']) || 0)} | Adicional: ${currency.format(Number(opcao?.Detalhes?.['Valor adicional']) || 0)}`}
                              </small>
                            </article>
                          ))}
                          {!visibleSimulacaoOptions.length ? (
                            <p className="screen-note">Nenhuma opcao de envio encontrada para o filtro selecionado.</p>
                          ) : null}
                        </div>
                      </>
                    )}
                  </section>
                </section>

                <section className="vendor-grid">
                  {visibleFretes.map((frete) => (
                    <article className="vendor-card frete-card" key={frete.id_frete}>
                      <h3>{formatFreteName(frete)}</h3>
                      <p>{`100g inicial: ¥${(Number(frete.valor_100g) || 0).toFixed(2)}`}</p>
                      <p>{`Cada 100g extra: ¥${(Number(frete.valor_100g_plus) || 0).toFixed(2)}`}</p>

                      <div className="frete-tags">
                        {Array.isArray(frete.modalidades) && frete.modalidades.length ? (
                          frete.modalidades.map((nomeModalidade, index) => (
                            <span className="frete-tag" key={`${frete.id_frete}-${nomeModalidade}-${index}`}>
                              {nomeModalidade}
                            </span>
                          ))
                        ) : (
                          <small>Sem modalidades associadas.</small>
                        )}
                      </div>
                    </article>
                  ))}
                </section>

                {!visibleFretes.length ? (
                  <div className="empty-state">
                    <h2>Nenhum frete encontrado</h2>
                    <p>Ajuste a busca/filtro de servico ou cadastre novos fretes na tela de cadastro.</p>
                  </div>
                ) : null}
              </>
            ) : null}

            {activeScreen === 'vendedores' ? (
              <>
                {editVendedorMessage ? <p className="form-success">{editVendedorMessage}</p> : null}

                <section className="vendor-grid">
                  {visibleVendedores.map((vendedor) => (
                    <article className="vendor-card" key={vendedor.id_vendedor}>
                      {editVendedorId === vendedor.id_vendedor ? (
                        <form className="vendor-edit-form" onSubmit={(event) => onUpdateVendedor(event, vendedor.id_vendedor)}>
                          <label htmlFor={`vendedorNomeEdit-${vendedor.id_vendedor}`}>Nome</label>
                          <input
                            id={`vendedorNomeEdit-${vendedor.id_vendedor}`}
                            type="text"
                            minLength={2}
                            maxLength={200}
                            value={editVendedorForm.nome}
                            onChange={(event) => setEditVendedorForm((prev) => ({ ...prev, nome: event.target.value }))}
                            required
                          />

                          <label htmlFor={`vendedorLojaEdit-${vendedor.id_vendedor}`}>Loja</label>
                          <input
                            id={`vendedorLojaEdit-${vendedor.id_vendedor}`}
                            type="text"
                            minLength={2}
                            maxLength={200}
                            value={editVendedorForm.loja}
                            onChange={(event) => setEditVendedorForm((prev) => ({ ...prev, loja: event.target.value }))}
                            required
                          />

                          <label htmlFor={`vendedorLinkEdit-${vendedor.id_vendedor}`}>Link da loja (nao editavel)</label>
                          <input
                            id={`vendedorLinkEdit-${vendedor.id_vendedor}`}
                            type="url"
                            value={editVendedorForm.link_loja}
                            readOnly
                          />

                          {editVendedorError ? <p className="form-error">{editVendedorError}</p> : null}

                          <div className="vendor-actions">
                            <button type="submit" className="ghost-btn primary-btn" disabled={updatingVendedor}>
                              {updatingVendedor ? 'Salvando...' : 'Salvar'}
                            </button>
                            <button type="button" className="ghost-btn" onClick={onCancelEditVendedor} disabled={updatingVendedor}>
                              Cancelar
                            </button>
                          </div>
                        </form>
                      ) : (
                        <>
                          <div className="vendor-title">
                            <h3>{safeText(vendedor.nome)}</h3>
                            {ultimoVendedorAcessadoId === vendedor.id_vendedor ? (
                              <span className="last-accessed-badge">Último acessado</span>
                            ) : null}
                          </div>
                          <p>{`Loja: ${safeText(vendedor.loja)}`}</p>
                          

                          <div className="vendor-actions">
                            <button type="button" className="ghost-btn success-btn" onClick={() => onOpenVendedor(vendedor)}>
                              Abrir
                            </button>
                            <button type="button" className="ghost-btn" onClick={() => onStartEditVendedor(vendedor)}>
                              Editar
                            </button>
                            <button
                              type="button"
                              className="ghost-btn danger-btn"
                              onClick={() => onDeleteVendedor(vendedor)}
                              disabled={deletingVendedorId === vendedor.id_vendedor}
                            >
                              {deletingVendedorId === vendedor.id_vendedor ? 'Removendo...' : 'Remover'}
                            </button>
                          </div>
                        </>
                      )}
                    </article>
                  ))}
                </section>

                {!visibleVendedores.length ? (
                  <div className="empty-state">
                    <h2>Nenhum vendedor encontrado</h2>
                    <p>Ajuste a busca ou cadastre vendedores na tela de cadastro.</p>
                  </div>
                ) : null}
              </>
            ) : null}

            {activeScreen === 'cadastro' ? (
              <>
                <p className="screen-note">Cadastre novos vendedores e produtos nesta tela. O cadastro de frete e restrito a ADMIN.</p>

                <section className="manage-grid">
                  <form className="manage-form" onSubmit={onCreateVendedor}>
                    <h3>Adicionar vendedor</h3>
                    <label htmlFor="vendedorNome">Nome</label>
                    <input
                      id="vendedorNome"
                      type="text"
                      minLength={2}
                      maxLength={200}
                      value={vendedorForm.nome}
                      onChange={(event) => setVendedorForm((prev) => ({ ...prev, nome: event.target.value }))}
                      required
                    />

                    <label htmlFor="vendedorLoja">Loja</label>
                    <input
                      id="vendedorLoja"
                      type="text"
                      minLength={2}
                      maxLength={200}
                      value={vendedorForm.loja}
                      onChange={(event) => setVendedorForm((prev) => ({ ...prev, loja: event.target.value }))}
                      required
                    />

                    <label htmlFor="vendedorLinkLoja">Link da loja (opcional)</label>
                    <input
                      id="vendedorLinkLoja"
                      type="url"
                      value={vendedorForm.link_loja}
                      onChange={(event) => setVendedorForm((prev) => ({ ...prev, link_loja: event.target.value }))}
                      placeholder="https://..."
                    />

                    {vendedorError ? <p className="form-error">{vendedorError}</p> : null}
                    {vendedorMessage ? <p className="form-success">{vendedorMessage}</p> : null}

                    <div className="dialog-actions">
                      <button type="submit" className="ghost-btn primary-btn" disabled={creatingVendedor}>
                        {creatingVendedor ? 'Salvando...' : 'Salvar vendedor'}
                      </button>
                    </div>
                  </form>

                  <form className="manage-form" onSubmit={onCreateProduto}>
                    <h3>Adicionar produto</h3>
                    <label htmlFor="produtoNome">Nome</label>
                    <input
                      id="produtoNome"
                      type="text"
                      minLength={2}
                      maxLength={250}
                      value={produtoForm.nome}
                      onChange={(event) => setProdutoForm((prev) => ({ ...prev, nome: event.target.value }))}
                      required
                    />

                    <label htmlFor="produtoLink">Link do produto</label>
                    <input
                      id="produtoLink"
                      type="url"
                      value={produtoForm.link_produto}
                      onChange={(event) => setProdutoForm((prev) => ({ ...prev, link_produto: event.target.value }))}
                      placeholder="https://..."
                      required
                    />

                    <label htmlFor="produtoImagem">Link da imagem (opcional)</label>
                    <input
                      id="produtoImagem"
                      type="url"
                      value={produtoForm.link_imagem}
                      onChange={(event) => setProdutoForm((prev) => ({ ...prev, link_imagem: event.target.value }))}
                      placeholder="https://..."
                    />

                    <div className="manage-inline">
                      <div>
                        <label htmlFor="produtoValor">Valor (yuan)</label>
                        <input
                          id="produtoValor"
                          type="number"
                          min="0.01"
                          step="0.01"
                          value={produtoForm.valor}
                          onChange={(event) => setProdutoForm((prev) => ({ ...prev, valor: event.target.value }))}
                          required
                        />
                      </div>
                      <div>
                        <label htmlFor="produtoPeso">Peso (g)</label>
                        <input
                          id="produtoPeso"
                          type="number"
                          min="1"
                          step="1"
                          value={produtoForm.peso}
                          onChange={(event) => setProdutoForm((prev) => ({ ...prev, peso: event.target.value }))}
                          required
                        />
                      </div>
                    </div>

                    <div className="manage-inline">
                      <div>
                        <label htmlFor="produtoModalidade">ID modalidade</label>
                        <input
                          id="produtoModalidade"
                          type="number"
                          min="1"
                          step="1"
                          value={produtoForm.id_modalidade}
                          onChange={(event) => setProdutoForm((prev) => ({ ...prev, id_modalidade: event.target.value }))}
                          required
                        />
                      </div>
                      <div>
                        <label htmlFor="produtoVendedor">Vendedor (opcional)</label>
                        <select
                          id="produtoVendedor"
                          value={produtoForm.id_vendedor}
                          onChange={(event) => setProdutoForm((prev) => ({ ...prev, id_vendedor: event.target.value }))}
                        >
                          <option value="">Sem vendedor</option>
                          {vendedores.map((vendedor) => (
                            <option key={vendedor.id_vendedor} value={vendedor.id_vendedor}>
                              {`${vendedor.nome} (${vendedor.loja})`}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>

                    {produtoError ? <p className="form-error">{produtoError}</p> : null}
                    {produtoMessage ? <p className="form-success">{produtoMessage}</p> : null}

                    <div className="dialog-actions">
                      <button type="submit" className="ghost-btn primary-btn" disabled={creatingProduto}>
                        {creatingProduto ? 'Salvando...' : 'Salvar produto'}
                      </button>
                    </div>
                  </form>

                  {isAdmin ? (
                    <form className="manage-form" onSubmit={onCreateFrete}>
                      <h3>Adicionar frete</h3>
                      <label htmlFor="freteNome">Nome do frete</label>
                      <input
                        id="freteNome"
                        type="text"
                        minLength={2}
                        maxLength={200}
                        value={freteForm.nome}
                        onChange={(event) => setFreteForm((prev) => ({ ...prev, nome: event.target.value }))}
                        required
                      />

                      <label htmlFor="freteServico">Servico (ex: Cssbuy)</label>
                      <input
                        id="freteServico"
                        type="text"
                        minLength={2}
                        maxLength={120}
                        value={freteForm.servico}
                        onChange={(event) => setFreteForm((prev) => ({ ...prev, servico: event.target.value }))}
                        required
                      />

                      <div className="manage-inline">
                        <div>
                          <label htmlFor="freteValorBase">Valor 100g (yuan)</label>
                          <input
                            id="freteValorBase"
                            type="number"
                            min="0.01"
                            step="0.01"
                            value={freteForm.valor_100g}
                            onChange={(event) => setFreteForm((prev) => ({ ...prev, valor_100g: event.target.value }))}
                            required
                          />
                        </div>
                        <div>
                          <label htmlFor="freteValorExtra">Valor 100g adicional (yuan)</label>
                          <input
                            id="freteValorExtra"
                            type="number"
                            min="0.01"
                            step="0.01"
                            value={freteForm.valor_100g_plus}
                            onChange={(event) => setFreteForm((prev) => ({ ...prev, valor_100g_plus: event.target.value }))}
                            required
                          />
                        </div>
                      </div>

                      <label>Modalidades atendidas</label>
                      <div className="modalidade-list">
                        {modalidades.length ? (
                          modalidades.map((modalidade) => {
                            const checked = freteForm.modalidades_ids.includes(modalidade.id_modalidade)
                            return (
                              <label className="modalidade-item" key={modalidade.id_modalidade}>
                                <input
                                  type="checkbox"
                                  checked={checked}
                                  onChange={() => onToggleFreteModalidade(modalidade.id_modalidade)}
                                />
                                <span>{modalidade.nome_modalidade}</span>
                              </label>
                            )
                          })
                        ) : (
                          <small>Sem modalidades carregadas no momento.</small>
                        )}
                      </div>

                      {freteError ? <p className="form-error">{freteError}</p> : null}
                      {freteMessage ? <p className="form-success">{freteMessage}</p> : null}

                      <div className="dialog-actions">
                        <button type="submit" className="ghost-btn primary-btn" disabled={creatingFrete}>
                          {creatingFrete ? 'Salvando...' : 'Salvar frete'}
                        </button>
                      </div>
                    </form>
                  ) : (
                    <section className="manage-form" aria-live="polite">
                      <h3>Gestao de frete</h3>
                      <p className="screen-note">Apenas usuarios ADMIN podem cadastrar ou editar fretes. Usuarios comuns podem apenas visualizar e simular.</p>
                    </section>
                  )}
                </section>
              </>
            ) : null}
          </>
        ) : null}
      </main>

      {authOpen ? (
        <div
          className="auth-overlay"
          role="dialog"
          aria-modal="true"
          aria-label="Autenticacao"
          onClick={(event) => {
            if (event.target === event.currentTarget) {
              setAuthOpen(false)
            }
          }}
        >
          <div className="auth-dialog">
            <div className="auth-switch">
              <button
                type="button"
                className={`ghost-btn ${authTab === 'login' ? 'primary-btn' : ''}`}
                onClick={() => setAuthTab('login')}
              >
                Entrar
              </button>
              <button
                type="button"
                className={`ghost-btn ${authTab === 'register' ? 'primary-btn' : ''}`}
                onClick={() => setAuthTab('register')}
              >
                Cadastrar
              </button>
              {!currentUser ? (
                <button
                  type="button"
                  className={`ghost-btn ${authTab === 'forgot' || authTab === 'reset' ? 'primary-btn' : ''}`}
                  onClick={() => {
                    setForgotError('')
                    setResetError('')
                    setResetMessage('')
                    setAuthTab(resetForm.token ? 'reset' : 'forgot')
                  }}
                >
                  Recuperar
                </button>
              ) : null}
              {currentUser ? (
                <button
                  type="button"
                  className={`ghost-btn ${authTab === 'password' ? 'primary-btn' : ''}`}
                  onClick={() => setAuthTab('password')}
                >
                  Trocar senha
                </button>
              ) : null}
            </div>

            {authTab === 'login' ? (
              <form className="register-form" onSubmit={onLogin}>
                <h2>Acessar conta</h2>
                <p>Entre para visualizar e gerenciar seus produtos.</p>

                <label htmlFor="loginUsername">Username</label>
                <input
                  id="loginUsername"
                  type="text"
                  autoComplete="username"
                  value={loginForm.username}
                  onChange={(event) => setLoginForm((prev) => ({ ...prev, username: event.target.value }))}
                  required
                />

                <label htmlFor="loginSenha">Senha</label>
                <input
                  id="loginSenha"
                  type="password"
                  autoComplete="current-password"
                  value={loginForm.senha}
                  onChange={(event) => setLoginForm((prev) => ({ ...prev, senha: event.target.value }))}
                  required
                />

                {loginError ? <p className="form-error">{loginError}</p> : null}

                <button
                  type="button"
                  className="text-link-btn"
                  onClick={() => {
                    setForgotError('')
                    setForgotMessage('')
                    setAuthTab('forgot')
                  }}
                >
                  Esqueci minha senha
                </button>

                <div className="dialog-actions">
                  <button type="submit" className="ghost-btn primary-btn" disabled={loggingIn}>
                    {loggingIn ? 'Entrando...' : 'Entrar'}
                  </button>
                  <button type="button" className="ghost-btn" onClick={() => setAuthOpen(false)}>
                    Fechar
                  </button>
                </div>
              </form>
            ) : authTab === 'register' ? (
              <form className="register-form" onSubmit={onRegister}>
                <h2>Criar conta</h2>
                <p>Seus produtos e vendedores ficam separados por usuario.</p>

                <label htmlFor="registerNome">Nome</label>
                <input
                  id="registerNome"
                  type="text"
                  minLength={2}
                  maxLength={200}
                  value={registerForm.nome}
                  onChange={(event) => setRegisterForm((prev) => ({ ...prev, nome: event.target.value }))}
                  required
                />

                <label htmlFor="registerEmail">E-mail</label>
                <input
                  id="registerEmail"
                  type="email"
                  autoComplete="email"
                  maxLength={255}
                  value={registerForm.email}
                  onChange={(event) => setRegisterForm((prev) => ({ ...prev, email: event.target.value }))}
                  placeholder="seu-email@dominio.com"
                />

                <label htmlFor="registerUsername">Username</label>
                <input
                  id="registerUsername"
                  type="text"
                  minLength={3}
                  maxLength={50}
                  value={registerForm.username}
                  onChange={(event) => setRegisterForm((prev) => ({ ...prev, username: event.target.value }))}
                  required
                />

                <label htmlFor="registerSenha">Senha</label>
                <input
                  id="registerSenha"
                  type="password"
                  minLength={8}
                  maxLength={120}
                  value={registerForm.senha}
                  onChange={(event) => setRegisterForm((prev) => ({ ...prev, senha: event.target.value }))}
                  required
                />
                <small className={`strength ${strength.level}`}>{`Forca da senha: ${registerForm.senha ? strength.label : '-'}`}</small>

                <label htmlFor="registerSenha2">Confirmar senha</label>
                <input
                  id="registerSenha2"
                  type="password"
                  minLength={8}
                  maxLength={120}
                  value={registerForm.senha2}
                  onChange={(event) => setRegisterForm((prev) => ({ ...prev, senha2: event.target.value }))}
                  required
                />

                {registerError ? <p className="form-error">{registerError}</p> : null}

                <div className="dialog-actions">
                  <button type="submit" className="ghost-btn primary-btn" disabled={registering}>
                    {registering ? 'Criando...' : 'Criar conta'}
                  </button>
                  <button type="button" className="ghost-btn" onClick={() => setAuthOpen(false)}>
                    Fechar
                  </button>
                </div>
              </form>
            ) : authTab === 'forgot' ? (
              <form className="register-form" onSubmit={onForgotPassword}>
                <h2>Recuperar acesso</h2>
                <p>Informe o e-mail da conta para receber o link de redefinicao.</p>

                <label htmlFor="forgotEmail">E-mail</label>
                <input
                  id="forgotEmail"
                  type="email"
                  autoComplete="email"
                  value={forgotForm.email}
                  onChange={(event) => setForgotForm({ email: event.target.value })}
                  required
                />

                {forgotError ? <p className="form-error">{forgotError}</p> : null}
                {forgotMessage ? <p className="form-success">{forgotMessage}</p> : null}

                <button
                  type="button"
                  className="text-link-btn"
                  onClick={() => {
                    setResetError('')
                    setResetMessage('')
                    setAuthTab('reset')
                  }}
                >
                  Ja tenho token de redefinicao
                </button>

                <div className="dialog-actions">
                  <button type="submit" className="ghost-btn primary-btn" disabled={requestingReset}>
                    {requestingReset ? 'Enviando...' : 'Enviar link'}
                  </button>
                  <button type="button" className="ghost-btn" onClick={() => setAuthOpen(false)}>
                    Fechar
                  </button>
                </div>
              </form>
            ) : authTab === 'reset' ? (
              <form className="register-form" onSubmit={onResetPassword}>
                <h2>Redefinir senha</h2>
                <p>Use o token recebido por e-mail e defina sua nova senha.</p>

                <label htmlFor="resetToken">Token</label>
                <input
                  id="resetToken"
                  type="text"
                  value={resetForm.token}
                  onChange={(event) => setResetForm((prev) => ({ ...prev, token: event.target.value }))}
                  required
                />

                <label htmlFor="resetNovaSenha">Nova senha</label>
                <input
                  id="resetNovaSenha"
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  maxLength={120}
                  value={resetForm.novaSenha}
                  onChange={(event) => setResetForm((prev) => ({ ...prev, novaSenha: event.target.value }))}
                  required
                />
                <small className={`strength ${resetStrength.level}`}>{`Forca da senha: ${resetForm.novaSenha ? resetStrength.label : '-'}`}</small>

                <label htmlFor="resetNovaSenha2">Confirmar nova senha</label>
                <input
                  id="resetNovaSenha2"
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  maxLength={120}
                  value={resetForm.novaSenha2}
                  onChange={(event) => setResetForm((prev) => ({ ...prev, novaSenha2: event.target.value }))}
                  required
                />

                {resetError ? <p className="form-error">{resetError}</p> : null}
                {resetMessage ? <p className="form-success">{resetMessage}</p> : null}

                <button type="button" className="text-link-btn" onClick={() => setAuthTab('login')}>
                  Voltar para login
                </button>

                <div className="dialog-actions">
                  <button type="submit" className="ghost-btn primary-btn" disabled={resettingPassword}>
                    {resettingPassword ? 'Redefinindo...' : 'Redefinir senha'}
                  </button>
                  <button type="button" className="ghost-btn" onClick={() => setAuthOpen(false)}>
                    Fechar
                  </button>
                </div>
              </form>
            ) : (
              <form className="register-form" onSubmit={onChangePassword}>
                <h2>Alterar senha</h2>
                <p>Informe sua senha atual e defina uma nova senha forte.</p>

                <label htmlFor="passwordAtual">Senha atual</label>
                <input
                  id="passwordAtual"
                  type="password"
                  autoComplete="current-password"
                  value={passwordForm.senhaAtual}
                  onChange={(event) => setPasswordForm((prev) => ({ ...prev, senhaAtual: event.target.value }))}
                  required
                />

                <label htmlFor="passwordNova">Nova senha</label>
                <input
                  id="passwordNova"
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  maxLength={120}
                  value={passwordForm.novaSenha}
                  onChange={(event) => setPasswordForm((prev) => ({ ...prev, novaSenha: event.target.value }))}
                  required
                />
                <small className={`strength ${passwordStrength.level}`}>{`Forca da senha: ${passwordForm.novaSenha ? passwordStrength.label : '-'}`}</small>

                <label htmlFor="passwordNova2">Confirmar nova senha</label>
                <input
                  id="passwordNova2"
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  maxLength={120}
                  value={passwordForm.novaSenha2}
                  onChange={(event) => setPasswordForm((prev) => ({ ...prev, novaSenha2: event.target.value }))}
                  required
                />

                {passwordError ? <p className="form-error">{passwordError}</p> : null}

                <div className="dialog-actions">
                  <button type="submit" className="ghost-btn primary-btn" disabled={changingPassword}>
                    {changingPassword ? 'Alterando...' : 'Atualizar senha'}
                  </button>
                  <button type="button" className="ghost-btn" onClick={() => setAuthOpen(false)}>
                    Fechar
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      ) : null}
    </>
  )
}

export default App
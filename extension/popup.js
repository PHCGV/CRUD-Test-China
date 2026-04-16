const els = {
  sessionText: document.getElementById("sessionText"),
  statusText: document.getElementById("statusText"),
  usernameInput: document.getElementById("usernameInput"),
  passwordInput: document.getElementById("passwordInput"),
  apiBaseInput: document.getElementById("apiBaseInput"),
  modalidadeInput: document.getElementById("modalidadeInput"),
  pesoInput: document.getElementById("pesoInput"),
  valorInput: document.getElementById("valorInput"),
  loginBtn: document.getElementById("loginBtn"),
  logoutBtn: document.getElementById("logoutBtn"),
  saveConfigBtn: document.getElementById("saveConfigBtn"),
};

function setStatus(message, kind = "") {
  els.statusText.textContent = message || "";
  els.statusText.className = "status";
  if (kind) {
    els.statusText.classList.add(kind);
  }
}

function sendMessage(type, payload = {}) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ type, ...payload }, (resp) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      resolve(resp);
    });
  });
}

function normalizeApiBase(value) {
  const trimmed = (value || "").trim();
  if (!trimmed) {
    return "http://127.0.0.1:8050";
  }
  return trimmed.replace(/\/$/, "");
}

function readPositiveInt(input, fallback) {
  const n = Number.parseInt(input, 10);
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

function readPositiveNumber(input, fallback) {
  const n = Number.parseFloat(input);
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

async function loadState() {
  try {
    const response = await sendMessage("REQUEST", { action: "extension:get-state" });
    if (!response?.ok) {
      throw new Error(response?.message || "Falha ao obter estado");
    }

    const { config = {}, session = {} } = response || {};

    els.apiBaseInput.value = config.apiBase || "http://127.0.0.1:8050";
    els.modalidadeInput.value = String(config.idModalidade || 1);
    els.pesoInput.value = String(config.pesoDefault || 100);
    els.valorInput.value = String(config.valorDefault || 1.0);

    if (session?.user?.username) {
      const sourceTag = session?.source === "main-app" ? " (via sistema principal)" : "";
      els.sessionText.textContent = `Autenticado como ${session.user.username}${sourceTag}`;
    } else {
      els.sessionText.textContent = "Não autenticado.";
    }
  } catch (error) {
    setStatus(error.message || "Erro ao carregar estado", "error");
  }
}

async function onLogin() {
  const username = (els.usernameInput.value || "").trim();
  const password = (els.passwordInput.value || "").trim();
  const apiBase = normalizeApiBase(els.apiBaseInput.value);

  if (!username || !password) {
    setStatus("Informe usuario e senha.", "error");
    return;
  }

  setStatus("Entrando...");

  try {
    const response = await sendMessage("REQUEST", {
      action: "extension:login",
      credentials: {
        username,
        senha: password,
        apiBase,
      },
    });

    if (!response?.ok) {
      throw new Error(response?.message || "Falha no login");
    }

    els.passwordInput.value = "";
    setStatus("Login realizado com sucesso.", "ok");
    await loadState();
  } catch (error) {
    setStatus(error.message || "Falha no login", "error");
  }
}

async function onLogout() {
  try {
    const response = await sendMessage("REQUEST", { action: "extension:logout" });
    if (!response?.ok) {
      throw new Error(response?.message || "Falha no logout");
    }
    setStatus("Sessao encerrada.", "ok");
    await loadState();
  } catch (error) {
    setStatus(error.message || "Falha no logout", "error");
  }
}

async function onSaveConfig() {
  const payload = {
    apiBase: normalizeApiBase(els.apiBaseInput.value),
    idModalidade: readPositiveInt(els.modalidadeInput.value, 1),
    pesoDefault: readPositiveInt(els.pesoInput.value, 100),
    valorDefault: readPositiveNumber(els.valorInput.value, 1.0),
  };

  try {
    const response = await sendMessage("REQUEST", {
      action: "extension:update-config",
      config: payload,
    });
    if (!response?.ok) {
      throw new Error(response?.message || "Falha ao salvar configuração");
    }
    setStatus("Configuração salva.", "ok");
    await loadState();
  } catch (error) {
    setStatus(error.message || "Falha ao salvar configuração", "error");
  }
}

els.loginBtn.addEventListener("click", onLogin);
els.logoutBtn.addEventListener("click", onLogout);
els.saveConfigBtn.addEventListener("click", onSaveConfig);

loadState();
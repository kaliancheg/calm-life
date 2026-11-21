/* ==============================================
   Письмо первому клиенту — клиентская логика
   ============================================== */

(function () {
  'use strict';

  // ---------- DOM-элементы ----------
  const themeBtn = document.getElementById('themeBtn');
  const chatMessages = document.getElementById('chat-messages');
  const letterForm = document.getElementById('letter-form');
  const sendBtn = document.getElementById('send-btn');
  const errorPop = document.getElementById('error-pop');

  const fields = {
    clientName: document.getElementById('client-name'),
    clientSphere: document.getElementById('client-sphere'),
    userService: document.getElementById('user-service'),
    userName: document.getElementById('user-name'),
  };

  const fieldWrappers = {
    clientName: document.getElementById('field-name'),
    clientSphere: document.getElementById('field-sphere'),
    userService: document.getElementById('field-service'),
    userName: document.getElementById('field-freelancer'),
  };

  // ---------- Тема ----------
  function setTheme(dark) {
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
    try {
      localStorage.setItem('theme', dark ? 'dark' : 'light');
    } catch {}
  }

  // Восстанавливаем тему из localStorage или системных настроек
  (function initTheme() {
    const saved = localStorage.getItem('theme');
    if (saved) {
      setTheme(saved === 'dark');
    } else {
      setTheme(!window.matchMedia('(prefers-color-scheme: light)').matches);
    }
  })();

  themeBtn.addEventListener('click', function () {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    setTheme(!isDark);
  });

  // ---------- Утилиты чата ----------
  function addMessage(text, cls) {
    const div = document.createElement('div');
    div.className = 'msg ' + cls;
    div.innerHTML = text;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return div;
  }

  function addUserMessage(text) {
    return addMessage(escapeHtml(text), 'msg-user');
  }

  function addBotMessage(text) {
    return addMessage(escapeHtml(text), 'msg-bot');
  }

  function addLetterMessage(letter) {
    const div = addMessage('', 'msg-letter');
    div.innerHTML =
      '<span class="msg-label">✉ Готовое письмо</span>' +
      escapeHtml(letter);
    // Кнопка «Скопировать письмо»
    const copyBtn = document.createElement('button');
    copyBtn.className = 'ghost';
    copyBtn.textContent = '📋 Скопировать письмо';
    copyBtn.style.marginTop = '10px';
    copyBtn.addEventListener('click', function () {
      navigator.clipboard.writeText(letter).then(function () {
        copyBtn.textContent = '✅ Скопировано!';
        setTimeout(function () {
          copyBtn.textContent = '📋 Скопировать письмо';
        }, 2000);
      }).catch(function () {
        copyBtn.textContent = 'Ошибка копирования';
      });
    });
    div.appendChild(copyBtn);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return div;
  }

  function addErrorMessage(text) {
    return addMessage(escapeHtml(text), 'msg-error');
  }

  function getAttemptsWord(n) {
    var mod10 = n % 10;
    var mod100 = n % 100;
    if (mod100 >= 11 && mod100 <= 19) return 'попыток';
    if (mod10 === 1) return 'попытка';
    if (mod10 >= 2 && mod10 <= 4) return 'попытки';
    return 'попыток';
  }

  function addTypingIndicator() {
    const div = document.createElement('div');
    div.className = 'msg msg-bot typing';
    div.innerHTML = '<i></i><i></i><i></i>';
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return div;
  }

  function escapeHtml(str) {
    var map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return str.replace(/[&<>"']/g, function (m) { return map[m]; });
  }

  // ---------- Валидация ----------
  function hideError() {
    errorPop.classList.remove('show');
    // Убираем подсветку ошибок с полей
    for (var key in fieldWrappers) {
      fieldWrappers[key].classList.remove('invalid');
    }
  }

  function showError() {
    errorPop.classList.add('show');
  }

  // Автоскрытие ошибки при вводе в любое поле
  for (var key in fields) {
    (function (field) {
      field.addEventListener('input', function () {
        fieldWrappers[key].classList.remove('invalid');
        if (!errorPop.querySelector('input, textarea')) {
          hideError();
        }
      });
    })(fields[key]);
  }

  // ---------- Отправка формы ----------
  letterForm.addEventListener('submit', function (e) {
    e.preventDefault();
    hideError();

    // Считываем значения
    var values = {};
    for (var key in fields) {
      values[key] = fields[key].value.trim();
    }

    // Валидация — все поля обязательны
    var hasEmpty = false;
    for (var key in values) {
      if (!values[key]) {
        fieldWrappers[key].classList.add('invalid');
        hasEmpty = true;
      }
    }

    if (hasEmpty) {
      showError();
      return;
    }

    // Блокируем форму
    sendBtn.disabled = true;
    sendBtn.textContent = 'Генерация…';

    // Показываем сообщение пользователя
    addUserMessage(
      '📋 Клиент: ' + values.clientName +
      '\n🏢 Сфера: ' + values.clientSphere +
      '\n🛠 Моя услуга: ' + values.userService +
      '\n👤 Я: ' + values.userName
    );

    // Отправляем запрос на сервер с повторными попытками
    var MAX_RETRIES = 5;
    var retryCount = 0;
    var formValues = values;

    function unlockForm() {
      sendBtn.disabled = false;
      sendBtn.textContent = 'Отправить';
    }

    function sendLetterRequest() {
      // Показываем индикатор печати
      var typing = addTypingIndicator();

      fetch('/api/letter', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          clientName: formValues.clientName,
          clientSphere: formValues.clientSphere,
          userService: formValues.userService,
          userName: formValues.userName,
        }),
      })
        .then(function (response) {
          return response.json().then(function (json) {
            return { ok: response.ok, data: json };
          });
        })
        .then(function (result) {
          // Убираем индикатор
          if (typing.parentNode) typing.parentNode.removeChild(typing);

          if (result.ok && result.data.letter) {
            if (retryCount > 0) {
              addBotMessage('✅ Письмо сгенерировано после ' + retryCount + ' ' + getAttemptsWord(retryCount) + '.');
            }
            addLetterMessage(result.data.letter);
            // Очищаем форму
            letterForm.reset();
            retryCount = 0;
            unlockForm();
          } else if (result.data.error && result.data.error.indexOf('пустой ответ') !== -1 && retryCount < MAX_RETRIES) {
            // Пустой ответ от AI — повторяем попытку
            retryCount++;
            addBotMessage(
              '⚠️ Попытка ' + retryCount + ' из ' + MAX_RETRIES + ': AI не ответил. Повторяю…'
            );
            // Небольшая задержка перед повтором
            setTimeout(sendLetterRequest, 1500);
          } else {
            if (retryCount >= MAX_RETRIES) {
              addErrorMessage('Не удалось сгенерировать письмо после ' + MAX_RETRIES + ' ' + getAttemptsWord(MAX_RETRIES) + '. Попробуйте позже.');
            } else {
              addErrorMessage(result.data.error || 'Что-то пошло не так. Попробуйте ещё раз.');
            }
            retryCount = 0;
            unlockForm();
          }
        })
        .catch(function (err) {
          console.error('Request error:', err);
          if (typing.parentNode) typing.parentNode.removeChild(typing);

          if (retryCount < MAX_RETRIES) {
            retryCount++;
            addBotMessage(
              '⚠️ Попытка ' + retryCount + ' из ' + MAX_RETRIES + ': ошибка соединения. Повторяю…'
            );
            setTimeout(sendLetterRequest, 1500);
          } else {
            addErrorMessage('Ошибка соединения. Проверьте интернет и попробуйте снова.');
            retryCount = 0;
            unlockForm();
          }
        });
    }

    sendLetterRequest();
  });
})();

const LINKS = {
  site: "https://pc-diag.ru/",
  download: "https://github.com/progerman666/pc-diag/releases/latest",
  vk: "https://vk.ru/club243150004",
  tg: "https://t.me/remont_teh_ru",
  github: "https://github.com/progerman666/pc-diag",
};

const WELCOME =
  "👋 Привет! Это бот <b>pc-diag</b> — бесплатной диагностики Windows.\n\n" +
  "За 60 секунд покажет:\n" +
  "• здоровье дисков и износ SSD (SMART)\n" +
  "• ошибки Event Log за 24 часа\n" +
  "• сеть: шлюз, DNS, пинг и потери пакетов\n" +
  "• службы, автозагрузку и «прожорливые» процессы\n\n" +
  "Скачай и проверь свой ПК:";

const KEYBOARD = {
  inline_keyboard: [
    [{ text: "⬇️ Скачать pc-diag", url: LINKS.download }],
    [
      { text: "🌐 Сайт", url: LINKS.site },
      { text: "💬 VK", url: LINKS.vk },
    ],
    [{ text: "📣 Telegram-канал", url: LINKS.tg }],
  ],
};

async function tg(env, method, payload) {
  const res = await fetch(
    "https://api.telegram.org/bot" + env.BOT_TOKEN + "/" + method,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {}),
    }
  );
  return res.json();
}

function sendMessage(env, chatId, text, markup) {
  return tg(env, "sendMessage", {
    chat_id: chatId,
    text,
    parse_mode: "HTML",
    disable_web_page_preview: true,
    reply_markup: markup,
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/") {
      return new Response("pc-diag bot is running", { status: 200 });
    }

    if (url.pathname === "/setup") {
      const key = url.searchParams.get("key");
      if (!key || key !== env.SETUP_KEY) {
        return new Response("forbidden", { status: 403 });
      }
      const origin = url.origin;
      const results = {};
      results.webhook = await tg(env, "setWebhook", {
        url: origin + "/webhook",
        allowed_updates: ["message"],
      });
      results.name = await tg(env, "setMyName", { name: "pc-diag" });
      results.description = await tg(env, "setMyDescription", {
        description:
          "pc-diag — бесплатная диагностика Windows за 60 секунд: SMART, Event Log, сеть и службы.",
      });
      results.shortDescription = await tg(env, "setMyShortDescription", {
        short_description: "Диагностика Windows за 60 секунд",
      });
      results.commands = await tg(env, "setMyCommands", {
        commands: [
          { command: "start", description: "Открыть меню и скачать pc-diag" },
          { command: "download", description: "Скачать pc-diag" },
          { command: "help", description: "Помощь" },
        ],
      });
      results.webhookInfo = await tg(env, "getWebhookInfo", {});
      return new Response(JSON.stringify(results, null, 2), {
        headers: { "Content-Type": "application/json; charset=utf-8" },
      });
    }

    if (request.method === "POST" && url.pathname === "/webhook") {
      let update;
      try {
        update = await request.json();
      } catch {
        return new Response("bad request", { status: 400 });
      }
      const msg = update.message || update.edited_message;
      if (msg && msg.chat) {
        const chatId = msg.chat.id;
        const text = (msg.text || "").trim().toLowerCase();
        if (text === "/start" || text === "/help") {
          await sendMessage(env, chatId, WELCOME, KEYBOARD);
        } else if (text === "/download") {
          await sendMessage(env, chatId, "⬇️ Скачать pc-diag:", {
            inline_keyboard: [[{ text: "Скачать (GitHub)", url: LINKS.download }]],
          });
        } else {
          await sendMessage(env, chatId, "Нажми /start, чтобы получить ссылки 👇", KEYBOARD);
        }
      }
      return new Response("ok");
    }

    return new Response("not found", { status: 404 });
  },
};
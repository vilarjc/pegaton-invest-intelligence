"""
Alert Dispatcher — Envía alertas por múltiples canales.
P0-03: Alert System | EP-FR-001

Canales: Telegram, Email (SMTP), Webhook (HTTP POST), In-App (DB)
"""
import logging
import json
import smtplib
import sqlite3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass

from backend.app.core.pegaton_config import get_db_path

logger = logging.getLogger(__name__)


@dataclass
class AlertMessage:
    rule_id: str
    rule_name: str
    condition_met: str
    actual_value: Optional[float]
    message: str
    channels: List[str]
    targets: Dict[str, str]
    severity: str = "warning"


class TelegramNotifier:
    """Envía alertas por Telegram Bot."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self._enabled = bool(bot_token and chat_id)

    def send(self, msg: AlertMessage) -> bool:
        if not self._enabled:
            logger.debug("Telegram notifier disabled (no token/chat_id)")
            return False

        try:
            import urllib.request
            text = f"🚨 *{msg.rule_name}*\n\n{msg.message}\n\nValor: {msg.actual_value}\nCondición: {msg.condition_met}\nSeveridad: {msg.severity}"
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = json.dumps({
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown",
            }).encode("utf-8")

            req = urllib.request.Request(
                url, data=data, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read())
                return result.get("ok", False)

        except Exception as e:
            logger.error(f"Error enviando alerta por Telegram: {e}")
            return False


class EmailNotifier:
    """Envía alertas por email (SMTP)."""

    def __init__(
        self,
        smtp_host: str = "localhost",
        smtp_port: int = 587,
        smtp_user: str = "",
        smtp_pass: str = "",
        from_email: str = "alerts@pegaton.ai",
        to_emails: List[str] = None,
        use_tls: bool = True,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_pass = smtp_pass
        self.from_email = from_email
        self.to_emails = to_emails or []
        self.use_tls = use_tls
        self._enabled = bool(smtp_host and to_emails)

    def send(self, msg: AlertMessage) -> bool:
        if not self._enabled:
            logger.debug("Email notifier disabled")
            return False

        try:
            message = MIMEMultipart()
            message["From"] = self.from_email
            message["To"] = ", ".join(self.to_emails)
            message["Subject"] = f"🔔 Alerta Pegaton: {msg.rule_name}"

            body = f"""
Alerta: {msg.rule_name}
Condición: {msg.condition_met}
Valor actual: {msg.actual_value}
Severidad: {msg.severity}
Detalle: {msg.message}
Generado: {datetime.now(timezone.utc).isoformat()}
"""
            message.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                if self.smtp_user and self.smtp_pass:
                    server.login(self.smtp_user, self.smtp_pass)
                server.sendmail(self.from_email, self.to_emails, message.as_string())

            return True

        except Exception as e:
            logger.error(f"Error enviando alerta por email: {e}")
            return False


class WebhookNotifier:
    """Envía alertas por HTTP POST a un webhook."""

    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None):
        self.url = url
        self.headers = headers or {"Content-Type": "application/json"}
        self._enabled = bool(url)

    def send(self, msg: AlertMessage) -> bool:
        if not self._enabled:
            logger.debug("Webhook notifier disabled")
            return False

        try:
            import urllib.request
            payload = {
                "rule_id": msg.rule_id,
                "rule_name": msg.rule_name,
                "condition_met": msg.condition_met,
                "actual_value": msg.actual_value,
                "message": msg.message,
                "severity": msg.severity,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.url, data=data, headers=self.headers, method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status in (200, 201, 204)

        except Exception as e:
            logger.error(f"Error enviando alerta por webhook: {e}")
            return False


class InAppNotifier:
    """Almacena alertas en la DB para consulta desde la UI."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_db_path()

    def send(self, msg: AlertMessage) -> bool:
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO alert_history (rule_id, triggered_at, condition_met, actual_value, message, channel, sent)
                VALUES (?, ?, ?, ?, ?, 'in_app', 1)
            """, (
                msg.rule_id,
                datetime.now(timezone.utc).isoformat(),
                msg.condition_met,
                msg.actual_value,
                msg.message,
            ))
            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error guardando alerta in-app: {e}")
            return False


class AlertDispatcher:
    """
    Despachador central de alertas.
    Envía alertas a múltiples canales configurados.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}

        # Inicializar canales
        self.channels: Dict[str, Any] = {}

        # Telegram
        telegram_cfg = config.get("telegram", {})
        if telegram_cfg.get("bot_token") and telegram_cfg.get("chat_id"):
            self.channels["telegram"] = TelegramNotifier(
                bot_token=telegram_cfg["bot_token"],
                chat_id=telegram_cfg["chat_id"],
            )

        # Email
        email_cfg = config.get("email", {})
        if email_cfg.get("smtp_host") and email_cfg.get("to_emails"):
            self.channels["email"] = EmailNotifier(
                smtp_host=email_cfg["smtp_host"],
                smtp_port=email_cfg.get("smtp_port", 587),
                smtp_user=email_cfg.get("smtp_user", ""),
                smtp_pass=email_cfg.get("smtp_pass", ""),
                from_email=email_cfg.get("from_email", "alerts@pegaton.ai"),
                to_emails=email_cfg["to_emails"],
            )

        # Webhook
        webhook_cfg = config.get("webhook", {})
        if webhook_cfg.get("url"):
            self.channels["webhook"] = WebhookNotifier(
                url=webhook_cfg["url"],
                headers=webhook_cfg.get("headers", {}),
            )

        # In-App (siempre activo)
        self.channels["in_app"] = InAppNotifier()

        logger.info(f"AlertDispatcher iniciado con canales: {list(self.channels.keys())}")

    def dispatch(self, msg: AlertMessage) -> Dict[str, bool]:
        """
        Envía la alerta a todos los canales especificados en la acción.
        Retorna dict con éxito/fracaso por canal.
        """
        results = {}
        for action in msg.channels:
            channel = self.channels.get(action)
            if channel:
                try:
                    results[action] = channel.send(msg)
                except Exception as e:
                    logger.error(f"Error en canal {action}: {e}")
                    results[action] = False
            else:
                logger.warning(f"Canal no configurado: {action}")
                results[action] = False

        return results

    def dispatch_simple(
        self,
        rule_id: str,
        rule_name: str,
        condition_met: str,
        actual_value: Optional[float] = None,
        message: str = "",
        channels: Optional[List[str]] = None,
        severity: str = "warning",
    ) -> Dict[str, bool]:
        """Envío simplificado de alerta."""
        msg = AlertMessage(
            rule_id=rule_id,
            rule_name=rule_name,
            condition_met=condition_met,
            actual_value=actual_value,
            message=message,
            channels=channels or ["in_app"],
            targets={},
            severity=severity,
        )
        return self.dispatch(msg)


# ── Singleton global ────────────────────────────────────────────

_dispatcher: Optional[AlertDispatcher] = None


def get_dispatcher(config: Optional[Dict[str, Any]] = None) -> AlertDispatcher:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = AlertDispatcher(config=config)
    return _dispatcher
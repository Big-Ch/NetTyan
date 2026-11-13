"""Local demo UI. It does not publish messages or open a public tunnel."""
import json
import os
import uuid
import secrets
from pathlib import Path
import gradio as gr

from kadr.runtime import CourseRuntime
from kadr.voice import synthesize,play_local
from kadr.session import GameSession
from kadr.game_chat import GameChat

CSS = """
.gradio-container {max-width: 1000px !important; margin: auto !important;}
.kadr-header {display:flex;gap:24px;align-items:center;padding:24px 0 16px;}
.kadr-header h1 {font-size:38px;letter-spacing:-1.6px;margin:0;}
.kadr-header p {color:#526158;margin:4px 0;}
footer {display:none !important;}
"""


def build_app(runtime=None,*,autonomous=False):
    runtime = runtime or CourseRuntime()
    session = GameSession(runtime)
    game_chat = GameChat(session)
    if autonomous:
        game_chat.start_default()
    secret_path = Path(__file__).resolve().parents[2] / "data" / "browser-secret.txt"
    if not secret_path.exists():
        secret_path.write_text(secrets.token_hex(16), encoding="utf-8")
    def send(message, history, identity, allow_memory, voice, game):
        try:
            result = runtime.reply(identity, message, allow_memory, game)
        except (ValueError, RuntimeError) as error:
            raise gr.Error(str(error)) from None
        history = list(history or []) + [{"role":"user", "content":message}, {"role":"assistant", "content":result["answer"]}]
        audio = None
        status = f"Ответ за {result['seconds']:.1f} с"
        if voice:
            try:
                audio = synthesize(result["answer"], runtime)
                if identity not in runtime.stopped:play_local(audio)
                else:audio=None
            except RuntimeError:
                status += ". Озвучка недоступна; текст сохранён."
        notes = "\n".join("- " + item["note"] for item in result["notes"]) or "Заметок пока нет."
        details = {k: result[k] for k in ("seconds", "tools", "spent_usd_estimate")}
        return "", history, audio, status, notes, details

    def restore(identity):
        try:
            user_id = runtime.user_id(identity)
            history = [{"role": item["role"], "content":item["content"]} for item in runtime.db.get_user_diags(user_id, count=4)]
            notes = "\n".join("- " + item["note"] for item in runtime.notes(identity)) or "Заметок пока нет."
            return history, notes, "Разговор восстановлен."
        except ValueError as error:
            raise gr.Error(str(error)) from None

    def forget(identity):
        return [], "Заметок пока нет.", runtime.forget(identity), None

    def start(identity):
        if not identity:
            identity = uuid.uuid4().hex
        history, notes, status = restore(identity)
        return identity, identity, history, notes, status

    def feedback(rating, comment):
        runtime.feedback(rating, comment)
        return "Спасибо. Отзыв сохранён."

    def start_game(identity,objective,voice):
        try:return session.start(identity,objective,voice)
        except ValueError as error:raise gr.Error(str(error)) from None

    def live(identity,seen):
        frame,state=session.observe()
        sound=gr.skip()
        history=gr.skip()
        if identity and session.identity==identity and session.version!=seen:
            history=[{'role':item['role'],'content':item['content']} for item in runtime.db.get_user_diags(runtime.user_id(identity),count=8)]
            sound=session.audio
            seen=session.version
        return frame,state,session.phase,sound,history,seen

    def stop_all(identity):
        game_chat.stop()
        return session.stop(identity)

    def listen_chat(allowed,voice,offer_homework=False):
        try:return game_chat.start(allowed,voice,offer_homework)
        except ValueError as error:raise gr.Error(str(error)) from None

    theme = gr.themes.Base(primary_hue="lime", neutral_hue="slate", font=["Inter", "Arial", "sans-serif"])
    with gr.Blocks(title="Кадр в роли Тайлера | Persona Lab", theme=theme, css=CSS, analytics_enabled=False) as demo:
        identity = gr.BrowserState(default_value=None, storage_key="kadr-identity-v2", secret=secret_path.read_text(encoding="utf-8"))
        gr.HTML('<div class="kadr-header"><div><h1>Кадр в роли Тайлера</h1><p>ИИ-персонаж. Домашки клуба в Minecraft.</p></div></div>')
        gr.Markdown('Minecraft, речь и память работают в одном сеансе. Сначала войди в свой тестовый мир выживания.')
        with gr.Row():
            game_image=gr.Image(label='Настоящий кадр Minecraft',type='pil',interactive=False)
            with gr.Column():
                objective=gr.Textbox(label='Игровая задача',value='Добудь дерево и сделай один верстак. Проверь, что верстак появился в инвентаре.')
                begin=gr.Button('Выполнить в Minecraft',variant='primary')
                game_phase=gr.Markdown('Игровая задача не запущена.')
                game_state=gr.JSON(label='Мир, задача и настоящий инвентарь')
        with gr.Accordion('Общение с игроками',open=False):
            allow_chat=gr.Checkbox(label='Разрешаю ответы Кадра в текущем игровом чате',value=False)
            offer_homework=gr.Checkbox(label='Подходить к игрокам и предлагать домашку',value=False)
            enable_chat=gr.Button('Включить игровой чат')
            chat_phase=gr.Markdown('Игровой чат отключён. Поддерживается формат Minecraft <Nick> текст.')
        seen_audio=gr.State(-1)
        gr.Markdown('Попробуй «Тайлер, дай домашку» или «Пас, я не в клубе».')
        chat = gr.Chatbot(type="messages", label="Разговор", height=370)
        message = gr.Textbox(label="Твоя реплика", placeholder="Тайлер, дай домашку", max_lines=4)
        with gr.Row():
            allow_memory = gr.Checkbox(label="Разрешаю сохранить заметку из этой реплики", value=False)
            voice = gr.Checkbox(label="Озвучивать ответы", value=True)
            game = gr.Checkbox(label="Учитывать Minecraft в разговоре", value=True)
        with gr.Row():
            submit = gr.Button("Отправить", variant="primary")
            stop = gr.Button("Остановить")
            resume = gr.Button("Продолжить")
        audio = gr.Audio(label="Голос Кадра, повторить запись", type="filepath", interactive=False, autoplay=False)
        status = gr.Markdown("Готов к разговору.")
        with gr.Accordion("Что Кадр запомнил", open=False):
            notes = gr.Markdown("Заметок пока нет.")
            gr.Markdown("На этом компьютере сохраняется история разговора. Кнопка ниже удаляет её вместе с заметками.")
            erase = gr.Button("Удалить мои заметки и историю", variant="stop")
        with gr.Accordion("Оставить отзыв", open=False):
            rating = gr.Slider(1, 5, value=3, step=1, label="Насколько хочется продолжить разговор?")
            comment = gr.Textbox(label="Что понравилось или помешало?", max_lines=4)
            feedback_button = gr.Button("Сохранить отзыв")
            feedback_status = gr.Markdown()
        with gr.Accordion("Для демонстрации", open=False):
            identity_display = gr.Textbox(label="Код возвращения к разговору", interactive=True)
            restore_button = gr.Button("Восстановить по коду")
            gr.Markdown("Код даёт доступ к этому разговору. Не показывайте его на публичной записи.")
            details = gr.JSON(label="Время, подтверждения инструментов и оценка расхода")
        demo.load(start, identity, [identity, identity_display, chat, notes, status])
        restore_button.click(lambda x:x, identity_display, identity).then(restore, identity, [chat,notes,status])
        inputs = [message,chat,identity,allow_memory,voice,game]
        outputs = [message,chat,audio,status,notes,details]
        submit.click(send, inputs, outputs, concurrency_limit=1)
        message.submit(send, inputs, outputs, concurrency_limit=1)
        begin.click(start_game,[identity,objective,voice],game_phase)
        timer=gr.Timer(1.0)
        timer.tick(live,[identity,seen_audio],[game_image,game_state,game_phase,audio,chat,seen_audio],queue=False,show_progress='hidden')
        timer.tick(lambda:game_chat.phase,outputs=chat_phase,queue=False,show_progress='hidden',api_name=False)
        enable_chat.click(listen_chat,[allow_chat,voice,offer_homework],chat_phase)
        stop.click(stop_all, identity, status, queue=False)
        resume.click(runtime.resume, identity, status, queue=False)
        erase.click(forget, identity, [chat,notes,status,audio])
        feedback_button.click(feedback, [rating,comment], feedback_status)
    return demo


def main():
    build_app(autonomous=True).queue().launch(server_name="127.0.0.1", server_port=22228, share=False, inbrowser=False)

if __name__ == "__main__":
    main()

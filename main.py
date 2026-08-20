import sys

from worker import AssistantWorker

from PySide6.QtWidgets import QApplication

from ui import AssistantSidebar


def main():
    app = QApplication(sys.argv)

    sidebar = AssistantSidebar()
    worker = AssistantWorker()

    worker.gesture_changed.connect(sidebar.set_active_gesture)
    worker.voice_status_changed.connect(sidebar.set_voice_status)
    worker.last_voice_changed.connect(sidebar.set_last_voice)
    worker.chat_message_added.connect(sidebar.add_chat_message)

    sidebar.voice_requested.connect(worker.request_voice_command)
    sidebar.camera_toggle_requested.connect(worker.toggle_camera_window)
    sidebar.chat_text_submitted.connect(worker.request_chat_text)
    sidebar.chat_voice_requested.connect(worker.request_chat_command)
    sidebar.close_requested.connect(worker.stop)

    sidebar.close_requested.connect(app.quit)
    app.aboutToQuit.connect(worker.stop)

    screen = app.primaryScreen().availableGeometry()

    sidebar_width = sidebar.expanded_width
    top_offset = 30

    x = screen.x() + screen.width() - sidebar_width
    y = screen.y() + top_offset
    height = screen.height() - top_offset

    sidebar.setGeometry(x, y, sidebar_width, height)

    sidebar.show()
    worker.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

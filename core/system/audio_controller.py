import sys
import winsound
import threading

class AudioFeedback:
    @staticmethod
    def play_activation():
        """Bip clássico sutil de ativação do J.A.R.V.I.S."""
        def _play():
            try:
                winsound.Beep(880, 80) # Lá (A5)
                winsound.Beep(1760, 100) # Lá (A6)
            except Exception:
                pass
        threading.Thread(target=_play, daemon=True).start()

    @staticmethod
    def play_alert():
        """Bip suave de alerta para confirmações preventivas."""
        def _play():
            try:
                winsound.Beep(1200, 120)
                winsound.Beep(900, 150)
            except Exception:
                pass
        threading.Thread(target=_play, daemon=True).start()

    @staticmethod
    def play_success():
        """Bip suave de conclusão e sucesso de tarefas."""
        def _play():
            try:
                winsound.Beep(1046, 80) # Dó (C6)
                winsound.Beep(1318, 120) # Mi (E6)
            except Exception:
                pass
        threading.Thread(target=_play, daemon=True).start()

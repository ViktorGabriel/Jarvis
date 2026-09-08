import { useState, useEffect, useRef, useCallback } from 'react';

interface UseSpeechRecognitionOptions {
  lang?: string;
  continuous?: boolean;
  interimResults?: boolean;
  onFinalResult?: (transcript: string) => void;
}

export function useSpeechRecognition({
  lang = 'pt-BR',
  continuous = true,
  interimResults = true,
  onFinalResult,
}: UseSpeechRecognitionOptions = {}) {
  const [isListening, setIsListening] = useState(false);
  const [interimTranscript, setInterimTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSupported, setIsSupported] = useState(false);

  const recognitionRef = useRef<any>(null);
  const shouldListenRef = useRef(false);
  const onFinalResultRef = useRef(onFinalResult);

  useEffect(() => {
    onFinalResultRef.current = onFinalResult;
  }, [onFinalResult]);

  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      setIsSupported(true);
      const recognition = new SpeechRecognition();
      recognition.lang = lang;
      recognition.continuous = continuous;
      recognition.interimResults = interimResults;
      recognition.maxAlternatives = 1;

      recognition.onstart = () => {
        setIsListening(true);
        setError(null);
      };

      recognition.onresult = (event: any) => {
        let finalStr = '';
        let interimStr = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const trans = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalStr += trans;
          } else {
            interimStr += trans;
          }
        }

        setInterimTranscript(interimStr);

        const cleanFinal = finalStr.trim();
        if (cleanFinal) {
          setInterimTranscript('');
          onFinalResultRef.current?.(cleanFinal);
        }
      };

      recognition.onerror = (event: any) => {
        // Erro 'no-speech' é normal quando o microfone está ocioso
        if (event.error !== 'no-speech') {
          console.warn('[HUD Voice] Erro no reconhecimento:', event.error);
          setError(event.error);
        }
      };

      recognition.onend = () => {
        setIsListening(false);
        // Reinicia automaticamente se o usuário não pediu para parar
        if (shouldListenRef.current) {
          try {
            recognition.start();
          } catch (e) {
            // Ignora tentativa de restart caso já esteja em transição
          }
        }
      };

      recognitionRef.current = recognition;
    } else {
      setIsSupported(false);
      setError('Reconhecimento de fala não suportado nesta plataforma.');
    }

    return () => {
      shouldListenRef.current = false;
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {}
      }
    };
  }, [lang, continuous, interimResults]);

  const startListening = useCallback(() => {
    if (!recognitionRef.current) return;
    shouldListenRef.current = true;
    try {
      recognitionRef.current.start();
    } catch (e) {
      // Caso já esteja iniciado
    }
  }, []);

  const stopListening = useCallback(() => {
    shouldListenRef.current = false;
    if (!recognitionRef.current) return;
    try {
      recognitionRef.current.stop();
    } catch (e) {}
    setIsListening(false);
    setInterimTranscript('');
  }, []);

  const toggleListening = useCallback(() => {
    if (isListening || shouldListenRef.current) {
      stopListening();
    } else {
      startListening();
    }
  }, [isListening, startListening, stopListening]);

  return {
    isListening,
    interimTranscript,
    isSupported,
    error,
    startListening,
    stopListening,
    toggleListening,
  };
}

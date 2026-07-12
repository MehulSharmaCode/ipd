// Voice Profile Input System - Web Speech API
// Supports: English (en-IN), Hindi (hi-IN), Marathi (mr-IN), Gujarati (gu-IN)

type NumericFields = 'phone_number' | 'age' | 'pincode' | 'aadhar_number' | 'annual_income' | 'land_size_hectares';

const NUMERIC_FIELDS: NumericFields[] = [
  'phone_number',
  'age',
  'pincode',
  'aadhar_number',
  'annual_income',
  'land_size_hectares',
];

export function useVoiceInput() {
  const isSupported =
    typeof window !== 'undefined' &&
    ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window);

  /**
   * Start listening for voice input for a specific field.
   * @param fieldKey - the form field key to fill
   * @param language - BCP47 language tag, e.g. 'en-IN', 'hi-IN'
   * @param onResult - callback with the transcribed (and optionally filtered) text
   * @param onError - callback for error messages
   * @param onListeningChange - callback to indicate start/stop listening
   */
  function listen(
    fieldKey: string,
    language: string,
    onResult: (value: string) => void,
    onError?: (msg: string) => void,
    onListeningChange?: (listening: boolean) => void
  ) {
    if (!isSupported) {
      onError?.('Voice input is not supported in your browser.');
      return;
    }

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    const recognition = new SpeechRecognition();
    recognition.lang = language;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.continuous = false;

    onListeningChange?.(true);

    recognition.onresult = (event: any) => {
      let transcript: string = event.results[0][0].transcript.trim();

      // Numeric fields: filter out everything except digits
      if (NUMERIC_FIELDS.includes(fieldKey as NumericFields)) {
        transcript = transcript.replace(/\D/g, '');
      }

      onResult(transcript);
      onListeningChange?.(false);
    };

    recognition.onerror = (event: any) => {
      onError?.(`Voice error: ${event.error}`);
      onListeningChange?.(false);
    };

    recognition.onend = () => {
      onListeningChange?.(false);
    };

    recognition.start();
  }

  return { isSupported, listen };
}

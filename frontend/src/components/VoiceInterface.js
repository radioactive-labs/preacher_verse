import React from 'react';
import { ThemeProvider, ConsoleTemplate } from '@pipecat-ai/voice-ui-kit';
import './VoiceInterface.css';

function VoiceInterface() {
  return (
    <ThemeProvider>
      <ConsoleTemplate
        transportType="smallwebrtc"
        connectParams={{
          webrtcUrl: "http://localhost:7860/api/offer",
        }}
        noUserVideo={true}
        config={{
          enableMic: true,
          enableCam: false,
        }}
      />
    </ThemeProvider>
  );
}

export default VoiceInterface;

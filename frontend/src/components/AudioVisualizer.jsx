import React, { useEffect, useRef } from "react";

/**
 * AudioVisualizer Component
 * Renders a simple frequency bar visualization or a "speaking orb" effect.
 * 
 * Props:
 * - stream: MediaStream | null
 * - isListening: boolean
 */
const AudioVisualizer = ({ stream, isListening }) => {
    const canvasRef = useRef(null);
    const animationRef = useRef(null);
    const audioContextRef = useRef(null);
    const analyserRef = useRef(null);
    const sourceRef = useRef(null);

    useEffect(() => {
        if (!stream || !isListening) {
            if (animationRef.current) cancelAnimationFrame(animationRef.current);
            return;
        }

        const canvas = canvasRef.current;
        const ctx = canvas.getContext("2d");

        // Init Audio Context
        if (!audioContextRef.current) {
            audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
        }
        const audioCtx = audioContextRef.current;

        // Create Analyser
        if (!analyserRef.current) {
            analyserRef.current = audioCtx.createAnalyser();
            analyserRef.current.fftSize = 256;
        }
        const analyser = analyserRef.current;

        // Connect Source
        if (!sourceRef.current) {
            sourceRef.current = audioCtx.createMediaStreamSource(stream);
            sourceRef.current.connect(analyser);
        }

        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        const draw = () => {
            animationRef.current = requestAnimationFrame(draw);
            analyser.getByteFrequencyData(dataArray);

            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // Aesthetic "Voice Orb" or "Waveform"
            // Let's do a symmetric mirrored bar graph for a "Siri-like" feel
            // or a simple neon waveform.

            const centerX = canvas.width / 2;
            const centerY = canvas.height / 2;

            // Calculate average volume for "glow" effect
            let sum = 0;
            for (let i = 0; i < bufferLength; i++) {
                sum += dataArray[i];
            }
            const avgVolume = sum / bufferLength;

            // Draw Glow
            const glowRadius = 10 + (avgVolume / 255) * 50;
            const gradient = ctx.createRadialGradient(centerX, centerY, 10, centerX, centerY, glowRadius * 2);
            gradient.addColorStop(0, "rgba(34, 211, 238, 0.8)"); // Cyan
            gradient.addColorStop(1, "rgba(34, 211, 238, 0)");

            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.arc(centerX, centerY, glowRadius, 0, 2 * Math.PI);
            ctx.fill();

            // Draw Bars
            ctx.fillStyle = "#22d3ee"; // Cyan-400
            const barWidth = (canvas.width / bufferLength) * 2.5;
            let x = 0;

            for (let i = 0; i < bufferLength; i++) {
                const barHeight = (dataArray[i] / 255) * canvas.height * 0.8;

                ctx.fillRect(x, centerY - barHeight / 2, barWidth, barHeight);
                x += barWidth + 1;
            }
        };

        draw();

        return () => {
            if (animationRef.current) cancelAnimationFrame(animationRef.current);
        };
    }, [stream, isListening]);

    return (
        <canvas
            ref={canvasRef}
            width={300}
            height={100}
            className={`w-full h-24 transition-opacity duration-500 ${isListening ? "opacity-100" : "opacity-0"}`}
        />
    );
};

export default AudioVisualizer;

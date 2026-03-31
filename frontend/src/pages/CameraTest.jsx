import { useEffect, useRef } from "react";

export default function CameraTest() {
  const videoRef = useRef(null);

  useEffect(() => {
    async function start() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });

        const video = videoRef.current;
        video.srcObject = stream;

        video.onloadeddata = () => {
          console.log("READY:", video.videoWidth, video.videoHeight);
          video.play();
        };

      } catch (err) {
        console.error("CAM ERROR:", err);
      }
    }

    start();
  }, []);

  return (
    <video
      ref={videoRef}
      autoPlay
      playsInline
      muted
      style={{ width: "400px", border: "3px solid red" }}
    />
  );
}

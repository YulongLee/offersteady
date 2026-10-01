import { useEffect, useRef, useState } from "react";

interface DeferredVideoProps {
  readonly label: string;
  readonly poster: string;
  readonly src: string;
}

export function DeferredVideo({ label, poster, src }: DeferredVideoProps) {
  const frame = useRef<HTMLDivElement>(null);
  const video = useRef<HTMLVideoElement>(null);
  const [nearViewport, setNearViewport] = useState(false);
  const [activated, setActivated] = useState(false);
  const [playbackNotice, setPlaybackNotice] = useState("");

  useEffect(() => {
    if (!frame.current || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(entries => {
      if (!entries.some(entry => entry.isIntersecting)) return;
      setNearViewport(true);
      observer.disconnect();
    }, { rootMargin: "200px" });
    observer.observe(frame.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!activated || !video.current) return;
    let disposed = false;
    // Controls remain available if the browser declines programmatic playback.
    void video.current.play()?.catch(() => {
      if (!disposed) setPlaybackNotice("Use the video controls to start playback.");
    });
    return () => { disposed = true; };
  }, [activated]);

  return <div ref={frame} className="global-product-film-frame deferred-video">
    <video ref={video} aria-label={label} controls={activated} muted playsInline preload="none"
      poster={nearViewport || activated ? poster : undefined} src={activated ? src : undefined}
      onError={() => setPlaybackNotice("Video could not load. Check your connection and use the video link to try again.")} />
    {!activated ? <button className="deferred-video-play" type="button" aria-label={`Play ${label}`} onClick={() => setActivated(true)}><span aria-hidden="true">▶</span> Play video</button> : null}
    {playbackNotice ? <p className="deferred-video-notice" role="status">{playbackNotice} <a href={src}>Open video</a></p> : null}
  </div>;
}

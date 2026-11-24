import { useState } from "react";

function coverUrl(url: string): string {
  return url.includes("/upload/")
    ? url.replace("/upload/", "/upload/c_fill,w_300,h_450,f_auto,q_auto/")
    : url;
}

export function BookIcon({ className = "" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 48 48" aria-hidden="true" focusable="false">
      <path d="M7 9c6-1.6 12-.4 17 3.5V40c-5-3.8-11-5-17-3.4V9Zm34 0c-6-1.6-12-.4-17 3.5V40c5-3.8 11-5 17-3.4V9Z" />
      <path d="M12 17c3.4-.7 6.1-.2 8.5 1.2M12 23c3.4-.7 6.1-.2 8.5 1.2m15-7.2c-3.4-.7-6.1-.2-8.5 1.2M35.5 23c-3.4-.7-6.1-.2-8.5 1.2" />
    </svg>
  );
}

export function BookCover({
  url,
  title,
  compact = false,
}: {
  url: string | null;
  title: string;
  compact?: boolean;
}) {
  const [failed, setFailed] = useState(false);
  return (
    <div className={`book-cover${compact ? " book-cover--compact" : ""}`}>
      {url && !failed ? (
        <img
          src={coverUrl(url)}
          alt={`Portada de ${title}`}
          loading="lazy"
          onError={() => setFailed(true)}
        />
      ) : (
        <div className="book-cover__placeholder" role="img" aria-label={`Sin portada: ${title}`}>
          <BookIcon />
          <span>{title}</span>
        </div>
      )}
    </div>
  );
}

import { useState } from "react";
import { Star } from "@phosphor-icons/react";

export default function RatingStars({ value = 0, onChange, readOnly = false, size = 26 }) {
  const [hover, setHover] = useState(0);
  const display = hover || value;

  return (
    <div className="rating-stars">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          disabled={readOnly}
          className={`rating-star-btn ${n <= display ? "filled" : ""}`}
          onMouseEnter={() => !readOnly && setHover(n)}
          onMouseLeave={() => !readOnly && setHover(0)}
          onClick={() => !readOnly && onChange?.(n)}
        >
          <Star size={size} weight={n <= display ? "fill" : "regular"} />
        </button>
      ))}
    </div>
  );
}

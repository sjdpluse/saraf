export default function Skeleton({ count = 3 }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {Array.from({ length: count }).map((_, i) => (
        <div className="skeleton skeleton-order-card" key={i} />
      ))}
    </div>
  );
}

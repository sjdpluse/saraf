import { CheckCircle, Circle, Clock, Package, XCircle } from "@phosphor-icons/react";

function formatTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleString("fa-IR-u-nu-latn", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function OrderTimeline({ order }) {
  const isCancelled = order.status === "cancelled";

  const steps = [
    {
      key: "created",
      title: "سفارش ثبت شد",
      time: order.created_at,
      state: "done",
    },
    {
      key: "review",
      title: isCancelled ? "بررسی شد" : order.status === "pending" ? "در حال بررسی توسط تیم ما" : "بررسی و تایید شد",
      time: order.confirmed_at || order.cancelled_at,
      state: isCancelled ? "cancelled" : order.confirmed_at ? "done" : "current",
    },
  ];

  if (isCancelled) {
    steps.push({
      key: "cancelled",
      title: "سفارش رد شد",
      time: order.cancelled_at,
      state: "cancelled",
    });
  } else {
    steps.push({
      key: "completed",
      title: "تکمیل شد",
      time: order.completed_at,
      state: order.completed_at ? "done" : order.confirmed_at ? "current" : "upcoming",
    });
  }

  return (
    <div className="order-timeline">
      {steps.map((step, i) => {
        const isLast = i === steps.length - 1;
        let Icon = Circle;
        if (step.state === "done") Icon = CheckCircle;
        else if (step.state === "cancelled") Icon = XCircle;
        else if (step.state === "current") Icon = Clock;
        else if (step.key === "completed") Icon = Package;

        return (
          <div className={`timeline-step ${step.state}`} key={step.key}>
            <div className="tl-marker-col">
              <div className="tl-dot">
                <Icon size={14} weight={step.state === "done" || step.state === "cancelled" ? "fill" : "bold"} />
              </div>
              {!isLast && <div className="tl-line" />}
            </div>
            <div className="tl-content">
              <div className="tl-title">{step.title}</div>
              {step.time && <div className="tl-time num">{formatTime(step.time)}</div>}
            </div>
          </div>
        );
      })}
    </div>
  );
}

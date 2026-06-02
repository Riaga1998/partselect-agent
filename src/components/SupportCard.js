import React from "react";
import "./SupportCard.css";

/**
 * Rendered when the agent calls escalate_to_support. `data` is the tool result:
 * { escalated, reason, order_id, contact: { phone, email, hours } }.
 */
function SupportCard({ data }) {
  const contact = data?.contact || {};
  return (
    <div className="support-card">
      <div className="support-head">
        <span className="support-icon">🎧</span>
        <span className="support-title">Connecting you with support</span>
      </div>
      {data?.reason && <p className="support-reason">Re: {data.reason}</p>}
      {data?.order_id && <p className="support-order">Order #{data.order_id}</p>}
      <ul className="support-contact">
        {contact.phone && <li><strong>Call</strong> {contact.phone}</li>}
        {contact.email && <li><strong>Email</strong> {contact.email}</li>}
        {contact.hours && <li><strong>Hours</strong> {contact.hours}</li>}
      </ul>
    </div>
  );
}

export default SupportCard;

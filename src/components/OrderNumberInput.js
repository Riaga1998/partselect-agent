import React, { useState } from "react";
import "./OrderNumberInput.css";

/**
 * Inline order-number entry, shown on a support-handoff turn when no order
 * number has been captured yet. Submitting sends the number into the chat so
 * the agent can include it in the support handoff.
 */
function OrderNumberInput({ onSubmit }) {
  const [value, setValue] = useState("");

  const submit = () => {
    const v = value.trim();
    if (!v) return;
    onSubmit(`My order number is ${v}`);
    setValue("");
  };

  return (
    <div className="order-input">
      <input
        className="order-input-field"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Enter your order number"
        onKeyPress={(e) => {
          if (e.key === "Enter") {
            submit();
            e.preventDefault();
          }
        }}
      />
      <button className="order-input-submit" onClick={submit}>
        Submit
      </button>
    </div>
  );
}

export default OrderNumberInput;

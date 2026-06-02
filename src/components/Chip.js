import React from "react";
import "./Chip.css";

function Chip({ label, onClick }) {
  return (
    <button className="chip" onClick={() => onClick(label)}>
      {label}
      <span className="chip-arrow">↗</span>
    </button>
  );
}

export default Chip;

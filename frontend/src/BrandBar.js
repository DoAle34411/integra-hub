import React from "react";

function BrandBar({ right }) {
  return (
    <div className="brand-bar">
      <div className="container d-flex align-items-center justify-content-between">
        <div>
          <div className="brand-title h4 m-0">UDLA IntegraHub</div>
          <div className="brand-subtitle">
            Innovación con estilo vino, pensado para ti
          </div>
        </div>
        <div>{right}</div>
      </div>
    </div>
  );
}

export default BrandBar;

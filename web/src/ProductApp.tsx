import { useState } from "react";
import DecisionLab from "./App";
import Overview from "./Overview";
import "./styles.css";

export default function ProductApp() {
  const [page, setPage] = useState<"overview" | "decision-lab">("overview");
  return <>
    <header className="product-nav"><div className="product-nav-inner"><span className="product-brand">PeopleOps Decision Lab <span className="demo-indicator">· Synthetic demo data</span></span><nav aria-label="Primary navigation"><button type="button" className={page === "overview" ? "nav-link active" : "nav-link"} aria-current={page === "overview" ? "page" : undefined} onClick={() => setPage("overview")}>Overview</button><button type="button" className={page === "decision-lab" ? "nav-link active" : "nav-link"} aria-current={page === "decision-lab" ? "page" : undefined} onClick={() => setPage("decision-lab")}>Decision Lab</button></nav></div></header>
    <p className="provenance-banner">Portfolio demo — all company and workforce data shown here are synthetic.</p>
    {page === "overview" ? <Overview onOpenDecisionLab={() => setPage("decision-lab")} /> : <DecisionLab />}
  </>;
}

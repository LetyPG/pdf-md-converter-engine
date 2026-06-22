import streamlit as st
import plotly.graph_objects as go

def _create_gauge(title: str, value: float, threshold: float, is_hard_fail: bool) -> go.Figure:
    """Creates a plotly gauge chart for a score."""
    if is_hard_fail:
        color = "green" if value == 100 else "red"
    else:
        color = "green" if value >= threshold else "orange"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 14}},
        gauge={
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': color},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'threshold': {
                'line': {'color': "red" if is_hard_fail else "orange", 'width': 4},
                'thickness': 0.75,
                'value': threshold
            }
        }
    ))
    fig.update_layout(height=200, margin=dict(l=10, r=10, t=40, b=10))
    return fig

def render_validation_panel(data: dict) -> None:
    """Displays validation scores and findings."""
    st.subheader("Quality Validation")

    passed = data.get("passed", False)
    if passed:
        st.success("✅ Artifact passed Quality Gate")
    else:
        st.error("❌ Artifact FAILED Quality Gate")

    # Overall Score prominent display
    st.metric("Overall Score", f"{data.get('overall_score', 0):.1f}/100")
    st.divider()

    # Dimension gauges
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.plotly_chart(_create_gauge("Structural", data.get("structural_score", 0), 95.0, False), use_container_width=True)
    with col2:
        st.plotly_chart(_create_gauge("Rendering", data.get("rendering_score", 0), 100.0, True), use_container_width=True)
    with col3:
        st.plotly_chart(_create_gauge("Security", data.get("security_score", 0), 100.0, True), use_container_width=True)
    with col4:
        st.plotly_chart(_create_gauge("Completeness", data.get("completeness_score", 0), 95.0, False), use_container_width=True)

    # Findings
    findings = data.get("findings", [])
    if findings:
        st.write("### Findings")
        for f in findings:
            sev = f.get("severity", "UNKNOWN")
            cat = f.get("category", "UNKNOWN")
            msg = f.get("message", "")
            loc = f.get("location", "")
            
            icon = "🔴" if sev == "ERROR" else "🟠" if sev == "WARNING" else "🔵"
            st.markdown(f"{icon} **[{cat}]** {msg} _({loc})_")
    else:
        st.info("No findings reported. Perfect artifact.")

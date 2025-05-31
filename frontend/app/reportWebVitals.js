const reportWebVitals = (onPerfEntry) => {
  if (onPerfEntry && typeof onPerfEntry === "function") {
    import("web-vitals").then(({ getCLS, getFID, getFCP, getLCP, getTTFB }) => {
      getCLS(onPerfEntry);
      getFID(onPerfEntry);
      getFCP(onPerfEntry);
      getLCP(onPerfEntry);
      getTTFB(onPerfEntry);
    });
  } else {
    // Default fallback: log metrics to console if no callback is provided
    import("web-vitals").then(({ getCLS, getFID, getFCP, getLCP, getTTFB }) => {
      const logMetric = (metric) => console.log(metric);
      getCLS(logMetric);
      getFID(logMetric);
      getFCP(logMetric);
      getLCP(logMetric);
      getTTFB(logMetric);
    });
  }
};

export default reportWebVitals;

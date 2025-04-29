// Advanced Visualizations for Paper Evolution

document.addEventListener("DOMContentLoaded", function() {
  initializeNetworkGraph();
  initializeTimeline();
});

// Network graph visualization for paper relationships
function initializeNetworkGraph() {
  const networkContainer = document.getElementById('network-graph');
  if (!networkContainer) return;
  
  // Create sample data for demonstration (in production, this would come from the backend)
  const papers = JSON.parse(networkContainer.dataset.papers || '[]');
  
  if (papers.length === 0) {
    networkContainer.innerHTML = '<p class="text-center">No paper data available for visualization.</p>';
    return;
  }
  
  // Prepare data for visualization
  const nodes = [];
  const edges = [];
  
  // Add papers as nodes
  papers.forEach((paper, index) => {
    nodes.push({
      id: index,
      label: paper.title,
      title: paper.title, // tooltip on hover
      value: 1 + Math.random() * 5, // node size
      group: paper.source // coloring by source
    });
    
    // Create random connections between papers (in production, this would be based on citations)
    // Connect to 1-3 random other papers
    const numConnections = Math.floor(1 + Math.random() * 3);
    for (let i = 0; i < numConnections; i++) {
      const targetIndex = Math.floor(Math.random() * papers.length);
      if (targetIndex !== index) { // avoid self-loops
        edges.push({
          from: index,
          to: targetIndex,
          width: 1 + Math.random() * 3,
          title: 'Related'
        });
      }
    }
  });

  // Check if vis.js is loaded
  if (typeof vis !== 'undefined') {
    // Create network graph
    const data = {
      nodes: new vis.DataSet(nodes),
      edges: new vis.DataSet(edges)
    };
    
    const options = {
      nodes: {
        shape: 'dot',
        scaling: {
          min: 10,
          max: 30
        },
        font: {
          size: 12,
          face: 'Inter'
        }
      },
      edges: {
        width: 0.15,
        color: { inherit: 'from' },
        smooth: {
          type: 'continuous'
        }
      },
      physics: {
        stabilization: false,
        barnesHut: {
          gravitationalConstant: -80000,
          springConstant: 0.001,
          springLength: 200
        }
      },
      interaction: {
        tooltipDelay: 200,
        hideEdgesOnDrag: true,
        multiselect: true
      }
    };

    // Initialize visualization
    new vis.Network(networkContainer, data, options);
  } else {
    // Fallback if vis.js is not available
    networkContainer.innerHTML = `
      <div class="vis-fallback">
        <h3>Network Visualization</h3>
        <p>The visualization library is not available. Please include vis.js in your project.</p>
        <p>You can add it with: <code>&lt;script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"&gt;&lt;/script&gt;</code></p>
      </div>
    `;
  }
}

// Timeline visualization for paper evolution
function initializeTimeline() {
  const timelineContainer = document.getElementById('papers-timeline');
  if (!timelineContainer) return;
  
  // Create sample data for demonstration (in production, this would come from the backend)
  const papers = JSON.parse(timelineContainer.dataset.papers || '[]');
  
  if (papers.length === 0) {
    timelineContainer.innerHTML = '<p class="text-center">No paper data available for timeline visualization.</p>';
    return;
  }
  
  // Check if the Timeline object from vis.js is available
  if (typeof vis !== 'undefined' && typeof vis.Timeline !== 'undefined') {
    // Prepare data for visualization
    const items = papers.map((paper, index) => {
      const year = paper.year || 2020; // Default to 2020 if no year available
      return {
        id: index,
        content: paper.title,
        title: `${paper.title}<br>Authors: ${paper.authors}<br>Source: ${paper.source}`,
        start: `${year}-01-01`
      };
    });

    // Create timeline
    const timeline = new vis.Timeline(
      timelineContainer,
      new vis.DataSet(items),
      {
        minHeight: '300px',
        maxHeight: '500px',
        stack: true,
        stackSubgroups: true,
        showMajorLabels: true,
        showCurrentTime: false,
        zoomable: true,
        orientation: 'top',
        margin: {
          item: 10,
          axis: 5
        }
      }
    );
  } else {
    // Fallback if vis.js is not available
    timelineContainer.innerHTML = `
      <div class="vis-fallback">
        <h3>Timeline Visualization</h3>
        <p>The visualization library is not available. Please include vis-timeline.js in your project.</p>
        <p>You can add it with: <code>&lt;script src="https://unpkg.com/vis-timeline/standalone/umd/vis-timeline.min.js"&gt;&lt;/script&gt;</code></p>
      </div>
    `;
  }
}
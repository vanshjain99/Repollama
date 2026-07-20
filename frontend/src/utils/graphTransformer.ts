import { MarkerType, type Node, type Edge } from "reactflow";

export interface ASTMetadata {
  functions: string[];
  classes: string[];
  imports: string[];
  parentFile?: string;
  language?: string;
  repoName?: string;
  relativePath?: string;
  incomingCount: number;
  outgoingCount: number;
}

export interface CustomNodeData {
  label: string;
  name: string;
  nodeType: string;
  language?: string;
  file_path?: string;
  repo_name?: string;
  astMetadata: ASTMetadata;
  rawId: string;
}

export interface NetworkXNode {
  id: string;
  name?: string;
  type?: string;
  language?: string;
  file_path?: string;
  relative_path?: string;
  repo_name?: string;
  [key: string]: any;
}

export interface NetworkXLink {
  source: string | { id: string };
  target: string | { id: string };
  type?: string;
  [key: string]: any;
}

export interface NetworkXGraphData {
  nodes: NetworkXNode[];
  links?: NetworkXLink[];
  edges?: NetworkXLink[];
}

/**
 * Normalizes a raw source or target from NetworkX link objects to a string ID.
 */
const getLinkId = (linkVal: string | { id: string }): string => {
  if (typeof linkVal === "object" && linkVal !== null && "id" in linkVal) {
    return String(linkVal.id);
  }
  return String(linkVal);
};

/**
 * Transforms raw NetworkX graph JSON into React Flow nodes and edges.
 * Performs AST metadata correlation and automatic 2D column layout.
 */
export function transformNetworkXToReactFlow(data: NetworkXGraphData): {
  nodes: Node<CustomNodeData>[];
  edges: Edge[];
} {
  const rawNodes = data.nodes || [];
  const rawLinks = data.links || data.edges || [];

  if (rawNodes.length === 0) {
    return { nodes: [], edges: [] };
  }

  // 1. Build lookup maps for edges and nodes
  const nodeMap = new Map<string, NetworkXNode>();
  rawNodes.forEach((n) => nodeMap.set(n.id, n));

  const outgoingMap = new Map<string, { target: string; type?: string }[]>();
  const incomingMap = new Map<string, { source: string; type?: string }[]>();

  rawLinks.forEach((link) => {
    const src = getLinkId(link.source);
    const tgt = getLinkId(link.target);
    const type = link.type;

    if (!outgoingMap.has(src)) outgoingMap.set(src, []);
    outgoingMap.get(src)!.push({ target: tgt, type });

    if (!incomingMap.has(tgt)) incomingMap.set(tgt, []);
    incomingMap.get(tgt)!.push({ source: src, type });
  });

  // 2. Classify nodes into layout columns/layers
  const layer0: NetworkXNode[] = []; // system / database
  const layer1: NetworkXNode[] = []; // file
  const layer2: NetworkXNode[] = []; // class
  const layer3: NetworkXNode[] = []; // function
  const layer4: NetworkXNode[] = []; // module / external imports

  rawNodes.forEach((node) => {
    const type = (node.type || "file").toLowerCase();
    if (type === "system" || type === "database") {
      layer0.push(node);
    } else if (type === "file") {
      layer1.push(node);
    } else if (type === "class") {
      layer2.push(node);
    } else if (type === "function") {
      layer3.push(node);
    } else {
      layer4.push(node);
    }
  });

  const layers = [layer0, layer1, layer2, layer3, layer4].filter(
    (l) => l.length > 0
  );

  const X_SPACING = 300;
  const Y_SPACING = 110;
  const positions = new Map<string, { x: number; y: number }>();

  layers.forEach((layerNodes, colIndex) => {
    const x = colIndex * X_SPACING + 50;
    const startY = 60;
    layerNodes.forEach((node, rowIndex) => {
      positions.set(node.id, {
        x,
        y: startY + rowIndex * Y_SPACING,
      });
    });
  });

  // 3. Construct React Flow Nodes with AST Metadata
  const rfNodes: Node<CustomNodeData>[] = rawNodes.map((node) => {
    const nodeId = node.id;
    const type = (node.type || "file").toLowerCase();
    const name =
      node.name ||
      node.relative_path ||
      nodeId.split("/").pop()?.split("::").pop() ||
      nodeId;

    const outEdges = outgoingMap.get(nodeId) || [];
    const inEdges = incomingMap.get(nodeId) || [];

    const functions: string[] = [];
    const classes: string[] = [];
    const imports: string[] = [];
    let parentFile: string | undefined = undefined;

    if (type === "file") {
      outEdges.forEach((e) => {
        const targetNode = nodeMap.get(e.target);
        if (e.type === "CONTAINS" && targetNode) {
          if (targetNode.type === "function") {
            functions.push(targetNode.name || targetNode.id);
          } else if (targetNode.type === "class") {
            classes.push(targetNode.name || targetNode.id);
          }
        } else if (e.type === "IMPORTS") {
          imports.push(e.target);
        }
      });
    } else if (type === "class" || type === "function") {
      const containsParent = inEdges.find((e) => e.type === "CONTAINS");
      if (containsParent) {
        parentFile = containsParent.source;
      }
      outEdges.forEach((e) => {
        if (e.type === "IMPORTS") {
          imports.push(e.target);
        }
      });
    } else if (type === "module") {
      inEdges.forEach((e) => {
        if (e.type === "IMPORTS") {
          imports.push(e.source);
        }
      });
    }

    const astMetadata: ASTMetadata = {
      functions,
      classes,
      imports,
      parentFile,
      language: node.language,
      repoName: node.repo_name,
      relativePath: node.relative_path || node.file_path,
      incomingCount: inEdges.length,
      outgoingCount: outEdges.length,
    };

    const pos = positions.get(nodeId) || { x: 100, y: 100 };

    return {
      id: nodeId,
      type: "customNode",
      position: pos,
      data: {
        label: name,
        name,
        nodeType: type,
        language: node.language,
        file_path: node.file_path || node.relative_path,
        repo_name: node.repo_name,
        astMetadata,
        rawId: nodeId,
      },
    };
  });

  // 4. Construct React Flow Edges
  const rfEdges: Edge[] = rawLinks.map((link, index) => {
    const src = getLinkId(link.source);
    const tgt = getLinkId(link.target);
    const edgeType = link.type || "CONTAINS";

    let strokeColor = "#8b5cf6";
    let isAnimated = false;
    let label = edgeType;

    if (edgeType === "IMPORTS") {
      strokeColor = "#0284c7"; // Sky blue
      isAnimated = true;
    } else if (edgeType === "CROSS_REPO_LINK") {
      strokeColor = "#f59e0b"; // Amber
      isAnimated = true;
    } else if (edgeType === "CONTAINS") {
      strokeColor = "#a855f7"; // Purple
    }

    return {
      id: `e-${src}-${tgt}-${index}`,
      source: src,
      target: tgt,
      type: "smoothstep",
      animated: isAnimated,
      label,
      labelStyle: { fill: "#a1a1aa", fontSize: 10, fontWeight: 500 },
      labelBgStyle: { fill: "#18181b", fillOpacity: 0.85, rx: 4, ry: 4 },
      style: { stroke: strokeColor, strokeWidth: 1.8 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: 14,
        height: 14,
        color: strokeColor,
      },
    };
  });

  return { nodes: rfNodes, edges: rfEdges };
}

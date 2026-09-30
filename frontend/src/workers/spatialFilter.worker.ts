/// <reference lib="webworker" />

interface FilterMessage {
  vessels: Record<string, any>;
  slicks: any[];
  vectors: any[];
  bbox: string;
}

self.onmessage = (e: MessageEvent<FilterMessage>) => {
  const { vessels, slicks, vectors, bbox } = e.data;
  
  const bboxParts = bbox ? bbox.split(',').map(Number) : null;
  const isBboxValid = bboxParts && bboxParts.length === 4 && bboxParts.every(n => !isNaN(n));
  const [minLon, minLat, maxLon, maxLat] = isBboxValid ? bboxParts : [-180, -90, 180, 90];

  const isInBbox = (lat: number, lon: number) => {
    if (!isBboxValid) return true;
    return lat >= minLat && lat <= maxLat && lon >= minLon && lon <= maxLon;
  };

  const visibleVessels = Object.values(vessels).filter(v => isInBbox(v.lat, v.lon));
  const visibleSlicks = slicks.filter(s => isInBbox(s.coordinates?.lat || s.lat, s.coordinates?.lon || s.lon));
  const visibleVectors = vectors.filter(d => isInBbox(d.lat, d.lon));

  self.postMessage({
    visibleVessels,
    visibleSlicks,
    visibleVectors
  });
};

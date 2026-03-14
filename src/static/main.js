const FACT_SLIDESHOW_INTERVAL = 8000; // 8 seconds


  async extractDominantColor(imageUrl) {
    return new Promise((resolve) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => {
        this.ctx.drawImage(img, 0, 0, 150, 150);
        const imageData = this.ctx.getImageData(0, 0, 150, 150).data;
        const color = this.calculateDominantColor(imageData);
        resolve(color);
      };
      img.onerror = () => resolve({ r: 29, g: 185, b: 84 }); // Default Spotify green
      img.src = imageUrl;
    });
  }

  calculateDominantColor(data) {
    const colors = [];
    const samples = 2000;
    
    // Collect all non-transparent colors (no brightness/saturation filtering)
    for (let i = 0; i < samples; i++) {
      const idx = Math.floor(Math.random() * (data.length / 4)) * 4;
      const r = data[idx];
      const g = data[idx + 1];
      const b = data[idx + 2];
      const a = data[idx + 3];
      
      // Only skip transparent pixels
      if (a < 128) continue;
      
      const max = Math.max(r, g, b);
      const min = Math.min(r, g, b);
      const saturation = max === 0 ? 0 : (max - min) / max;
      const brightness = (r + g + b) / 3;
      
      colors.push({ r, g, b, saturation, brightness });
    }
    
    if (colors.length === 0) {
      return { r: 29, g: 185, b: 84 }; // Default Spotify green
    }
    
    // Quantize and group colors
    const colorGroups = {};
    
    for (const color of colors) {
      // Use 32-step for finer granularity
      const qr = Math.round(color.r / 32) * 32;
      const qg = Math.round(color.g / 32) * 32;
      const qb = Math.round(color.b / 32) * 32;
      const key = `${qr},${qg},${qb}`;
      
      if (!colorGroups[key]) {
        colorGroups[key] = { 
          r: qr, g: qg, b: qb, 
          count: 0, 
          totalSaturation: 0,
          totalBrightness: 0
        };
      }
      
      colorGroups[key].count++;
      colorGroups[key].totalSaturation += color.saturation;
      colorGroups[key].totalBrightness += color.brightness;
    }
    
    // Calculate average values for each group
    const candidates = Object.values(colorGroups).map(group => ({
      r: group.r,
      g: group.g,
      b: group.b,
      count: group.count,
      avgSaturation: group.totalSaturation / group.count,
      avgBrightness: group.totalBrightness / group.count
    }));
    
    // Calculate scores for each color group
    candidates.forEach(candidate => {
      // Frequency score (normalized) - how common is this color
      const frequencyScore = candidate.count / samples;
      
      // Weighted saturation - saturation matters more for brighter colors
      // Dark colors with "high saturation" are misleading (e.g., rgb(0,0,32))
      const brightnessFactor = Math.min(1, candidate.avgBrightness / 100); // 0-1 scale, caps at brightness 100
      const saturationScore = candidate.avgSaturation * brightnessFactor;
      
      // Brightness score - prefer mid-to-bright tones that are visible
      // Use a curve that peaks around 150-180 (good for UI)
      const optimalBrightness = 160;
      const brightnessDist = Math.abs(candidate.avgBrightness - optimalBrightness) / 160;
      const brightnessScore = Math.max(0, 1 - brightnessDist);
      
      // Combined score:
      // - Frequency is most important (50%)
      // - Brightness balance ensures UI visibility (35%)
      // - Saturation adds preference for colorful tones, but weighted by brightness (15%)
      candidate.score = (frequencyScore * 0.50) + (brightnessScore * 0.35) + (saturationScore * 0.15);
    });
    
    // Sort by score and return the best
    candidates.sort((a, b) => b.score - a.score);
    
    // Debug: Log top candidates
    console.log('Top 5 color candidates:', candidates.slice(0, 5).map(c => ({
      rgb: `rgb(${c.r},${c.g},${c.b})`,
      count: c.count,
      score: c.score.toFixed(3),
      saturation: c.avgSaturation.toFixed(3),
      brightness: c.avgBrightness.toFixed(0)
    })));
    
    const best = candidates[0];
    console.log('Selected color:', `rgb(${best.r},${best.g},${best.b})`);
    
    // Ensure minimum brightness for UI visibility
    const brightness = (best.r + best.g + best.b) / 3;
    const minBrightness = 100; // Ensure progress bar and UI elements are visible
    
    if (brightness < minBrightness) {
      const factor = minBrightness / brightness;
      return {
        r: Math.min(255, Math.round(best.r * factor)),
        g: Math.min(255, Math.round(best.g * factor)),
        b: Math.min(255, Math.round(best.b * factor))
      };
    }
    
    return { r: best.r, g: best.g, b: best.b };
  }

  rgbToHex(r, g, b) {
    return `#${[r, g, b].map(x => x.toString(16).padStart(2, '0')).join('')}`;
  }
}

// Dynamic theme manager
class ThemeManager {
  constructor() {
    this.colorExtractor = new ColorExtractor();
    this.currentColor = { r: 29, g: 185, b: 84 };
    this.transitionDuration = 1000;
  }

  async updateTheme(imageUrl) {
    try {
      const color = await this.colorExtractor.extractDominantColor(imageUrl);
      this.applyColor(color);
      this.currentColor = color;
    } catch (error) {
      console.warn('Failed to extract color:', error);
    }
  }

  applyColor(color) {
    const root = document.documentElement;
    const { r, g, b } = color;
    
    // Adjust color for better visibility (ensure minimum brightness)
    const brightness = (r * 299 + g * 587 + b * 114) / 1000;
    const minBrightness = 80;
    
    let adjustedR = r, adjustedG = g, adjustedB = b;
    if (brightness < minBrightness) {
      const factor = minBrightness / brightness;
      adjustedR = Math.min(255, Math.round(r * factor));
      adjustedG = Math.min(255, Math.round(g * factor));
      adjustedB = Math.min(255, Math.round(b * factor));
    }
    
    // Apply CSS variables
    root.style.setProperty('--dynamic-rgb', `${adjustedR}, ${adjustedG}, ${adjustedB}`);
    root.style.setProperty('--dynamic-color', `rgb(${adjustedR}, ${adjustedG}, ${adjustedB})`);
    root.style.setProperty('--glow-color', `rgba(${adjustedR}, ${adjustedG}, ${adjustedB}, 0.3)`);
    root.style.setProperty('--gradient-start', `rgba(${adjustedR}, ${adjustedG}, ${adjustedB}, 0.15)`);
  }

  resetTheme() {
    this.applyColor({ r: 29, g: 185, b: 84 });
  }
}

// Progress bar manager
class ProgressManager {
  constructor() {
    this.progressFill = document.getElementById('progressFill');
    this.currentTimeEl = document.getElementById('currentTime');
    this.totalTimeEl = document.getElementById('totalTime');
    this.container = document.getElementById('progressContainer');
    this.animationId = null;
    this.lastProgress = 0;
    this.lastUpdateTime = 0;
  }

  show() {
    this.container.classList.add('visible');
  }

  hide() {
    this.container.classList.remove('visible');
  }

  update(progressMs, durationMs) {
    console.log('ProgressManager.update called:', progressMs, durationMs);
    if (!progressMs || !durationMs) {
      console.log('Hiding progress bar - missing data');
      this.hide();
      return;
    }

    console.log('Showing progress bar');
    this.show();
    this.lastProgress = progressMs;
    this.lastUpdateTime = Date.now();
    this.duration = durationMs;

    const progress = Math.min((progressMs / durationMs) * 100, 100);
    this.progressFill.style.width = `${progress}%`;

    this.currentTimeEl.textContent = this.formatTime(progressMs);
    this.totalTimeEl.textContent = this.formatTime(durationMs);

    // Start smooth animation
    this.startAnimation();
  }

    let factIntervalId = null;
    let previousFacts = null; // Track the facts from the previous message

    source.onmessage = (event) => {
        // console.log("SongInfo:", event.data);
        
        const data = JSON.parse(event.data);
        if (data.is_playing) {
            console.log("Currently playing:", data.item.name);
            // Update song title, artist, album art, and artist's intent
            document.querySelector("#songTitle").textContent = data.item.name;
            document.querySelector("#albumArt").src = data.item.album.images[0].url;
            document.querySelector("#songArtists").textContent = data.item.artists.map(artist => artist.name).join(", ");
            document.querySelector("#artistIntent").textContent = data.meaning;
        }
        const currentFacts = data.facts;

        // Only restart the carousel if the facts have changed (e.g., new song)
        const factsChanged = JSON.stringify(currentFacts) !== JSON.stringify(previousFacts);
        if (factsChanged) {
            if (factIntervalId) {
                clearInterval(factIntervalId);
            }
            factIntervalId = factCarousel(currentFacts);
            previousFacts = currentFacts; // Update the tracked facts
        }
    };

    this.animationId = requestAnimationFrame(animate);
  }

  stop() {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }
  }

  formatTime(ms) {
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  }
}

// Main application
window.onload = function() {
  // Check session
  const sessionId = document.cookie.split('; ').find(row => row.startsWith('SESSIONID='));
  if (!sessionId) {
    window.location.href = '/authorize';
    return;
  }

  // Initialize managers
  const themeManager = new ThemeManager();
  const progressManager = new ProgressManager();

  // UI Elements
  const songTitle = document.getElementById('songTitle');
  const songArtists = document.getElementById('songArtists');
  const albumArt = document.getElementById('albumArt');
  const artistIntent = document.getElementById('artistIntent');
  const songFact = document.getElementById('songFact');
  const playingOverlay = document.getElementById('playingOverlay');
  const nowPlayingIndicator = document.querySelector('.now-playing-indicator');
  const statusText = document.querySelector('.status-text');
  const factDots = document.getElementById('factDots');

  // State
  let factIntervalId = null;
  let previousFacts = null;
  let previousSongId = null;
  let isPlaying = false;

  // Connect to SSE
  const source = new EventSource('/xray');

  source.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    // Debug logging
    console.log('SSE data:', {
      is_playing: data.is_playing,
      has_item: !!data.item,
      progress_ms: data.progress_ms,
      duration_ms: data.item?.duration_ms,
      song_name: data.item?.name
    });
    
    // Handle playback state
    if (data.is_playing) {
      if (!isPlaying) {
        isPlaying = true;
        playingOverlay.classList.add('visible');
        nowPlayingIndicator.classList.add('active');
        statusText.textContent = 'Playing';
      }

      // Update song info
      const currentSongId = data.item.id;
      const songChanged = currentSongId !== previousSongId;

    function factCarousel(facts) {
        const factElement = document.querySelector("#songFact");
        
        if (!facts || facts.length === 0) {
            // factElement.textContent = "No interesting facts available for this song.";
            return null;
        }

        let currentFactIndex = 0;
        
        // Display the first fact immediately
        factElement.textContent = facts[currentFactIndex];

        // Update artist intent with animation
        updateTextWithAnimation(artistIntent, data.meaning || 'Analysis not available yet...');
      }

      // Update progress bar
      console.log('Updating progress bar:', data.progress_ms, data.item.duration_ms);
      progressManager.update(data.progress_ms, data.item.duration_ms);

    } else {
      if (isPlaying) {
        isPlaying = false;
        playingOverlay.classList.remove('visible');
        nowPlayingIndicator.classList.remove('active');
        statusText.textContent = 'Paused';
        progressManager.stop();
      }
    }

        return intervalId;
    }
};

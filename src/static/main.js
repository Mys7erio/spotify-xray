const FACT_SLIDESHOW_INTERVAL = 8000; // 8 seconds

// Color extraction utility for dynamic theming
class ColorExtractor {
  constructor() {
    this.canvas = document.createElement('canvas');
    this.ctx = this.canvas.getContext('2d', { willReadFrequently: true });
    this.canvas.width = 150;
    this.canvas.height = 150;
  }

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
    
    // Calculate diversity score (how different this color is from others)
    const totalColors = candidates.length;
    candidates.forEach(candidate => {
      // Frequency score (normalized)
      const frequencyScore = candidate.count / samples;
      
      // Saturation score (prefer colorful, but not exclusively)
      const saturationScore = candidate.avgSaturation;
      
      // Brightness preference: slightly favor mid-tones for UI visibility
      // but still allow dark/bright if they're dominant
      const brightnessScore = 1 - Math.abs(candidate.avgBrightness - 128) / 128;
      
      // Combined score: frequency matters most, then saturation, then brightness balance
      candidate.score = (frequencyScore * 0.6) + (saturationScore * 0.25) + (brightnessScore * 0.15);
    });
    
    // Sort by score and return the best
    candidates.sort((a, b) => b.score - a.score);
    
    const best = candidates[0];
    
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

  startAnimation() {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
    }

    const animate = () => {
      const elapsed = Date.now() - this.lastUpdateTime;
      const currentProgress = this.lastProgress + elapsed;
      
      if (currentProgress < this.duration) {
        const progress = (currentProgress / this.duration) * 100;
        this.progressFill.style.width = `${progress}%`;
        this.currentTimeEl.textContent = this.formatTime(currentProgress);
        this.animationId = requestAnimationFrame(animate);
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

      if (songChanged) {
        previousSongId = currentSongId;
        
        // Animate content update
        songTitle.classList.add('content-transition');
        songArtists.classList.add('content-transition');
        
        setTimeout(() => {
          songTitle.classList.remove('content-transition');
          songArtists.classList.remove('content-transition');
        }, 500);

        // Update text content
        songTitle.textContent = data.item.name;
        songArtists.textContent = data.item.artists.map(a => a.name).join(', ');
        
        // Update album art with crossfade
        const newImageUrl = data.item.album.images[0]?.url || 'assets/not-found.png';
        crossfadeImage(albumArt, newImageUrl);
        
        // Update theme based on album art
        themeManager.updateTheme(newImageUrl);

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

    // Handle facts (independent of playing state)
    const currentFacts = data.facts || [];
    const factsChanged = JSON.stringify(currentFacts) !== JSON.stringify(previousFacts);
    
    if (factsChanged) {
      if (factIntervalId) {
        clearInterval(factIntervalId);
      }
      
      if (currentFacts.length > 0) {
        factIntervalId = startFactCarousel(currentFacts);
        createFactDots(currentFacts.length);
      } else {
        songFact.innerHTML = '<span class="shimmer-text">Interesting facts will appear here</span>';
        factDots.innerHTML = '';
      }
      
      previousFacts = currentFacts;
    }
  };

  source.addEventListener('error', (e) => {
    console.error('EventSource error:', e);
    statusText.textContent = 'Disconnected';
    nowPlayingIndicator.classList.remove('active');
    progressManager.stop();
  });

  // Crossfade image transition
  function crossfadeImage(imgElement, newSrc) {
    if (imgElement.src === newSrc) return;
    
    imgElement.style.opacity = '0';
    imgElement.style.transform = 'scale(0.95)';
    
    setTimeout(() => {
      imgElement.src = newSrc;
      imgElement.onload = () => {
        imgElement.style.opacity = '1';
        imgElement.style.transform = 'scale(1)';
      };
    }, 300);
  }

  // Text update with animation
  function updateTextWithAnimation(element, newText) {
    element.style.opacity = '0';
    element.style.transform = 'translateY(10px)';
    
    setTimeout(() => {
      element.textContent = newText;
      element.classList.add('fade-text');
      element.style.opacity = '1';
      element.style.transform = 'translateY(0)';
      
      setTimeout(() => {
        element.classList.remove('fade-text');
      }, 600);
    }, 200);
  }

  // Create fact indicator dots
  function createFactDots(count) {
    factDots.innerHTML = '';
    for (let i = 0; i < count; i++) {
      const dot = document.createElement('span');
      dot.className = 'fact-dot' + (i === 0 ? ' active' : '');
      factDots.appendChild(dot);
    }
  }

  // Update active dot
  function updateActiveDot(index) {
    const dots = factDots.querySelectorAll('.fact-dot');
    dots.forEach((dot, i) => {
      dot.classList.toggle('active', i === index);
    });
  }

  // Fact carousel
  function startFactCarousel(facts) {
    if (!facts || facts.length === 0) return null;

    let currentIndex = 0;
    
    // Display first fact
    updateTextWithAnimation(songFact, facts[0]);
    updateActiveDot(0);

    // Start interval
    const intervalId = setInterval(() => {
      currentIndex = (currentIndex + 1) % facts.length;
      updateTextWithAnimation(songFact, facts[currentIndex]);
      updateActiveDot(currentIndex);
    }, FACT_SLIDESHOW_INTERVAL);

    return intervalId;
  }

  // Cleanup on page unload
  window.addEventListener('beforeunload', () => {
    progressManager.stop();
    if (factIntervalId) clearInterval(factIntervalId);
    source.close();
  });
};

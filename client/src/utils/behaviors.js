const easeOutElastic = (x) => {
  const c4 = (2 * Math.PI) / 3;
  return x === 0 ? 0 : x === 1 ? 1 : Math.pow(2, -10 * x) * Math.sin((x * 10 - 0.75) * c4) + 1;
};

const easeInOutQuad = (x) => {
  return x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2;
};

export const BEHAVIORS = [
  {
    name: 'charming_wink',
    duration: 3.0,
    apply: (_, p) => {
      const t = easeInOutQuad(Math.sin(p * Math.PI));
      const wink = p > 0.42 && p < 0.60 ? 1 : 0;
      return {
        joy: 0.6 * t,
        blink: 0.85 * wink,
        fun: 0.3 * t,
        neckZ: -0.15 * t, 
        headY: -0.1 * t,
        headX: 0.05 * t
      };
    }
  },
  {
    name: 'surprised_gasp',
    duration: 2.5,
    apply: (_, p) => {
      const t = easeOutElastic(p); 
      const fade = Math.sin(p * Math.PI);
      return {
        surprised: 0.8 * fade,
        joy: 0.1 * fade,
        blink: 0,
        neckX: -0.1 * fade, 
        headX: -0.15 * fade, 
        chestX: 0.2 * fade 
      };
    }
  },
  {
    name: 'deep_breath_relax',
    duration: 5.0,
    apply: (_, p) => {
      const t = Math.sin(p * Math.PI);
      return {
        joy: 0.2 * t,
        sorrow: 0.1 * t,
        blink: p > 0.3 && p < 0.7 ? 1 : 0, 
        chestX: 0.15 * t, 
        neckX: -0.05 * t, 
        headX: 0.1 * t,
        spineY: 0.02 * t 
      };
    }
  },
  {
    name: 'playful_shake',
    duration: 3.5,
    apply: (_, p) => {
      const fade = Math.sin(p * Math.PI);
      const shake = Math.sin(p * Math.PI * 6) * 0.1; 
      return {
        fun: 0.7 * fade,
        joy: 0.4 * fade,
        blink: Math.abs(shake) > 0.08 ? 1 : 0, 
        neckY: shake * fade, 
        headZ: shake * 0.5 * fade,
        headX: 0.05 * fade
      };
    }
  },
  {
    name: 'confused_tilt',
    duration: 4.0,
    apply: (_, p) => {
      const t = easeInOutQuad(Math.sin(p * Math.PI));
      return {
        fun: 0.3 * t,
        sorrow: 0.1 * t,
        blink: p > 0.8 ? 1 : 0,
        headZ: 0.2 * t, 
        neckY: 0.1 * t,
        headX: 0.1 * t
      };
    }
  },
  {
    name: 'happy_wave',
    duration: 3.0,
    apply: (_, p) => {
      const fade = Math.sin(p * Math.PI);
      return {
        joy: 0.6 * fade,
        fun: 0.4 * fade,
        chestY: 0.05 * fade
      };
    }
  },
  {
    name: 'sad_shrug',
    duration: 2.5,
    apply: (_, p) => {
      const t = easeInOutQuad(Math.sin(p * Math.PI));
      return {
        sorrow: 0.6 * t,
        chestX: -0.1 * t
      };
    }
  },
  {
    name: 'surprised_raise',
    duration: 2.2,
    apply: (_, p) => {
      const fade = easeOutElastic(p);
      return {
        surprised: 0.9 * Math.sin(p * Math.PI),
        headX: -0.1 * fade,
        chestX: 0.2 * fade
      };
    }
  },
  {
    name: 'confused_scratch',
    duration: 3.2,
    apply: (_, p) => {
      const t = easeInOutQuad(Math.sin(p * Math.PI));
      return {
        fun: 0.2 * t,
        blink: p > 0.6 ? 1 : 0,
        neckY: 0.1 * t,
        headZ: 0.15 * t
      };
    }
  },
  {
    name: 'oh_pose',
    duration: 2.8,
    apply: (_, p) => {
      const t = Math.sin(p * Math.PI);
      return {
        oh: 0.7 * t,
        chestX: 0.1 * t
      };
    }
  }
];

export function getRandomBehavior() {
  return BEHAVIORS[Math.floor(Math.random() * BEHAVIORS.length)];
}

export function getBehaviorForEmotion(emotion) {
  const weights = {
    happy: { happy_wave: 3, playful_shake: 2, deep_breath_relax: 1, charming_wink: 1 },
    sad: { sad_shrug: 3, deep_breath_relax: 2, confused_tilt: 1 },
    surprised: { surprised_raise: 3, surprised_gasp: 2, oh_pose: 1 },
    confused: { confused_tilt: 2, confused_scratch: 2, playful_shake: 1 },
    oh: { oh_pose: 3, surprised_gasp: 2, charming_wink: 1 },
    neutral: { deep_breath_relax: 2, charming_wink: 1, playful_shake: 1, confused_tilt: 1 }
  };
  const table = weights[emotion] || weights['neutral'];
  const names = Object.keys(table);
  const total = names.reduce((acc, n) => acc + table[n], 0);
  let r = Math.random() * total;
  let chosen = names[0];
  for (const n of names) {
    r -= table[n];
    if (r <= 0) {
      chosen = n;
      break;
    }
  }
  const b = BEHAVIORS.find(x => x.name === chosen);
  return b || getRandomBehavior();
}
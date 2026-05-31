// Animation variants for Framer Motion
// SaaS-style: subtle, professional, 0.2-0.3s duration

// Cubic bezier for ease-in-out
const easeInOut: [number, number, number, number] = [0.4, 0, 0.2, 1];
const easeOut: [number, number, number, number] = [0.4, 0, 0.6, 1];

export const transitions = {
  default: {
    duration: 0.25,
    ease: easeInOut,
  },
  fast: {
    duration: 0.2,
    ease: easeInOut,
  },
  slow: {
    duration: 0.3,
    ease: easeInOut,
  },
  spring: {
    type: 'spring' as const,
    stiffness: 300,
    damping: 30,
  },
};

// Page transitions
export const pageVariants = {
  initial: {
    opacity: 0,
    x: 8,
  },
  animate: {
    opacity: 1,
    x: 0,
  },
  exit: {
    opacity: 0,
    x: -8,
  },
};

export const pageTransition = {
  duration: 0.25,
  ease: easeInOut,
};

// Fade transition (for content swaps)
export const fadeVariants = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
};

export const fadeTransition = {
  duration: 0.2,
  ease: 'easeInOut',
};

// Stagger container for lists
export const staggerContainer = {
  animate: {
    transition: {
      staggerChildren: 0.05,
      delayChildren: 0.05,
    },
  },
};

export const staggerItem = {
  initial: { opacity: 0, y: 8 },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.2,
      ease: easeInOut,
    },
  },
};

// Card hover animation (for framer motion whileHover)
export const cardHover = {
  scale: 1.01,
  y: -2,
  transition: {
    duration: 0.2,
    ease: easeInOut,
  },
};

// Button tap animation
export const buttonTap = {
  scale: 0.98,
  transition: {
    duration: 0.1,
  },
};

// Sidebar slide animation
export const sidebarVariants = {
  open: {
    x: 0,
    transition: {
      duration: 0.3,
      ease: easeInOut,
    },
  },
  closed: {
    x: '-100%',
    transition: {
      duration: 0.3,
      ease: easeOut,
    },
  },
};

// Overlay fade
export const overlayVariants = {
  open: {
    opacity: 1,
    transition: {
      duration: 0.2,
      ease: easeInOut,
    },
  },
  closed: {
    opacity: 0,
    transition: {
      duration: 0.25,
      ease: easeOut,
    },
  },
};

// Skeleton to content fade
export const contentFadeVariants = {
  hidden: {
    opacity: 0,
    transition: {
      duration: 0.15,
      ease: easeInOut,
    },
  },
  visible: {
    opacity: 1,
    transition: {
      duration: 0.25,
      delay: 0.1,
      ease: easeInOut,
    },
  },
};

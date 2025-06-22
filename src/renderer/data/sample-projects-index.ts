/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

/**
 * Index of sample projects in the new folder-based format.
 * Each project is stored in sample_projects/<project_name>/<project_name>.atlasvibe
 */

export interface SampleProjectInfo {
  name: string;
  displayName: string;
  description: string;
  path: string; // Relative to app root
}

export const SAMPLE_PROJECTS: Record<string, SampleProjectInfo> = {
  default: {
    name: "default",
    displayName: "Noisy Sine",
    description: "Basic example with sine wave, random noise, and visualization",
    path: "sample_projects/default/default.atlasvibe",
  },
  fft: {
    name: "fft",
    displayName: "FFT Analysis",
    description: "Fast Fourier Transform example",
    path: "sample_projects/fft/fft.atlasvibe",
  },
  ifft: {
    name: "ifft",
    displayName: "Inverse FFT",
    description: "Inverse Fast Fourier Transform example",
    path: "sample_projects/ifft/ifft.atlasvibe",
  },
  butterworth: {
    name: "butterworth",
    displayName: "Butterworth Filter",
    description: "Digital signal processing with Butterworth filter",
    path: "sample_projects/butterworth/butterworth.atlasvibe",
  },
  fir: {
    name: "fir",
    displayName: "FIR Filter",
    description: "Finite Impulse Response filter example",
    path: "sample_projects/fir/fir.atlasvibe",
  },
  pid: {
    name: "pid",
    displayName: "PID Controller",
    description: "Proportional-Integral-Derivative controller example",
    path: "sample_projects/pid/pid.atlasvibe",
  },
  loop: {
    name: "loop",
    displayName: "Loop Example",
    description: "Demonstrates loop control flow",
    path: "sample_projects/loop/loop.atlasvibe",
  },
  images: {
    name: "images",
    displayName: "Image Processing",
    description: "Basic image manipulation example",
    path: "sample_projects/images/images.atlasvibe",
  },
  imageCaptioning: {
    name: "imageCaptioning",
    displayName: "Image Captioning",
    description: "AI-powered image captioning with ViT-GPT2",
    path: "sample_projects/imageCaptioning/imageCaptioning.atlasvibe",
  },
  imageClassification: {
    name: "imageClassification",
    displayName: "Image Classification",
    description: "Image classification with neural networks",
    path: "sample_projects/imageClassification/imageClassification.atlasvibe",
  },
  objectDetection: {
    name: "objectDetection",
    displayName: "Object Detection",
    description: "Detect objects in images using YOLO",
    path: "sample_projects/objectDetection/objectDetection.atlasvibe",
  },
  prophet: {
    name: "prophet",
    displayName: "Time Series Forecasting",
    description: "Time series analysis with Prophet",
    path: "sample_projects/prophet/prophet.atlasvibe",
  },
  arduino: {
    name: "arduino",
    displayName: "Arduino Serial",
    description: "Read data from Arduino via serial port",
    path: "sample_projects/arduino/arduino.atlasvibe",
  },
  labjack: {
    name: "labjack",
    displayName: "LabJack DAQ",
    description: "Data acquisition with LabJack hardware",
    path: "sample_projects/labjack/labjack.atlasvibe",
  },
  webcam: {
    name: "webcam",
    displayName: "Webcam Capture",
    description: "Capture and process webcam images",
    path: "sample_projects/webcam/webcam.atlasvibe",
  },
  stepper: {
    name: "stepper",
    displayName: "Stepper Motor",
    description: "Control stepper motors",
    path: "sample_projects/stepper/stepper.atlasvibe",
  },
  canSend: {
    name: "canSend",
    displayName: "CAN Bus Send",
    description: "Send messages over CAN bus",
    path: "sample_projects/canSend/canSend.atlasvibe",
  },
  canReadAndLog: {
    name: "canReadAndLog",
    displayName: "CAN Bus Logger",
    description: "Read and log CAN bus messages",
    path: "sample_projects/canReadAndLog/canReadAndLog.atlasvibe",
  },
  i2cDecode: {
    name: "i2cDecode",
    displayName: "I2C Decoder",
    description: "Decode I2C protocol messages",
    path: "sample_projects/i2cDecode/i2cDecode.atlasvibe",
  },
  MSO24DecodeI2C: {
    name: "MSO24DecodeI2C",
    displayName: "MSO24 I2C Decode",
    description: "I2C decoding with Tektronix MSO24",
    path: "sample_projects/MSO24DecodeI2C/MSO24DecodeI2C.atlasvibe",
  },
  leCroyExtractTrace: {
    name: "leCroyExtractTrace",
    displayName: "LeCroy Trace Extract",
    description: "Extract traces from LeCroy oscilloscope",
    path: "sample_projects/leCroyExtractTrace/leCroyExtractTrace.atlasvibe",
  },
  mdo3ExtractTrace: {
    name: "mdo3ExtractTrace",
    displayName: "MDO3000 Trace Extract",
    description: "Extract traces from Tektronix MDO3000",
    path: "sample_projects/mdo3ExtractTrace/mdo3ExtractTrace.atlasvibe",
  },
  picoExtractTrace: {
    name: "picoExtractTrace",
    displayName: "PicoScope Trace Extract",
    description: "Extract traces from PicoScope",
    path: "sample_projects/picoExtractTrace/picoExtractTrace.atlasvibe",
  },
  rigolExtractTrace: {
    name: "rigolExtractTrace",
    displayName: "Rigol Trace Extract",
    description: "Extract traces from Rigol oscilloscope",
    path: "sample_projects/rigolExtractTrace/rigolExtractTrace.atlasvibe",
  },
  dmmRead: {
    name: "dmmRead",
    displayName: "DMM Reading",
    description: "Read measurements from digital multimeter",
    path: "sample_projects/dmmRead/dmmRead.atlasvibe",
  },
  cDAQReadAnalog: {
    name: "cDAQReadAnalog",
    displayName: "NI cDAQ Analog Input",
    description: "Read analog inputs from NI CompactDAQ",
    path: "sample_projects/cDAQReadAnalog/cDAQReadAnalog.atlasvibe",
  },
  IVSweep: {
    name: "IVSweep",
    displayName: "IV Sweep",
    description: "Current-voltage characteristic measurement",
    path: "sample_projects/IVSweep/IVSweep.atlasvibe",
  },
  bodePlot: {
    name: "bodePlot",
    displayName: "Bode Plot",
    description: "Frequency response analysis",
    path: "sample_projects/bodePlot/bodePlot.atlasvibe",
  },
  atlasvibe: {
    name: "atlasvibe",
    displayName: "AtlasVibe Demo",
    description: "Comprehensive AtlasVibe feature demonstration",
    path: "sample_projects/atlasvibe/atlasvibe.atlasvibe",
  },
};

// Helper to get sample project by name
export function getSampleProject(name: string): SampleProjectInfo | undefined {
  return SAMPLE_PROJECTS[name];
}

// Get all sample projects as array
export function getAllSampleProjects(): SampleProjectInfo[] {
  return Object.values(SAMPLE_PROJECTS);
}

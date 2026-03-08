import React, { useState, useRef, useEffect } from 'react';
import { View, TouchableOpacity, Text, StyleSheet, Animated, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Audio } from 'expo-av';

interface VoiceButtonProps {
  onRecordingComplete: (audioUri: string) => void;
  isProcessing: boolean;
}

export function VoiceButton({ onRecordingComplete, isProcessing }: VoiceButtonProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (isRecording) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.2, duration: 500, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 500, useNativeDriver: true }),
        ])
      ).start();
    } else {
      pulseAnim.stopAnimation();
      pulseAnim.setValue(1);
    }
  }, [isRecording]);

  const startRecording = async () => {
    try {
      await Audio.requestPermissionsAsync();
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording: newRecording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      setRecording(newRecording);
      setIsRecording(true);
    } catch (error) {
      console.error('Failed to start recording:', error);
    }
  };

  const stopRecording = async () => {
    if (!recording) return;

    try {
      setIsRecording(false);
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      setRecording(null);
      
      if (uri) {
        onRecordingComplete(uri);
      }
    } catch (error) {
      console.error('Failed to stop recording:', error);
    }
  };

  const handlePress = () => {
    if (isProcessing) return;
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return (
    <Animated.View style={[styles.container, { transform: [{ scale: pulseAnim }] }]}>
      <TouchableOpacity
        style={[
          styles.button,
          isRecording && styles.buttonRecording,
          isProcessing && styles.buttonProcessing,
        ]}
        onPress={handlePress}
        disabled={isProcessing}
      >
        <Ionicons
          name={isRecording ? 'stop' : isProcessing ? 'hourglass' : 'mic'}
          size={32}
          color="#fff"
        />
      </TouchableOpacity>
      <Text style={styles.label}>
        {isProcessing ? 'Processing...' : isRecording ? 'Tap to stop' : 'Tap to speak'}
      </Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
  },
  button: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: '#4A90D9',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#4A90D9',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  buttonRecording: {
    backgroundColor: '#E74C3C',
  },
  buttonProcessing: {
    backgroundColor: '#95A5A6',
  },
  label: {
    marginTop: 8,
    fontSize: 12,
    color: '#666',
  },
});

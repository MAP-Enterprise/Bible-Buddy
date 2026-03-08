import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  Animated,
  ActivityIndicator,
  Dimensions,
  StatusBar,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import * as Speech from 'expo-speech';
import { Audio } from 'expo-av';
import { storage } from '../helpers/storage';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
const { width } = Dimensions.get('window');

const AGE_TIERS = [
  { value: '4-6', label: '4-6', color: '#FF6B6B', emoji: '🧒' },
  { value: '7-9', label: '7-9', color: '#4ECDC4', emoji: '👧' },
  { value: '10-12', label: '10-12', color: '#FFD93D', emoji: '🧑' },
  { value: '13-18', label: '13-18', color: '#6C5CE7', emoji: '🎓' },
];

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  audioUrl?: string;
  bibleVerses?: string[];
  fromKnowledgeBase?: boolean;
  timestamp: Date;
}

export default function ChatScreen() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [ageTier, setAgeTier] = useState('7-9');
  const [childId, setChildId] = useState('guest_child');
  const [showSettings, setShowSettings] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  
  const scrollViewRef = useRef<ScrollView>(null);
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const bounceAnim = useRef(new Animated.Value(0)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    loadSettings();
    Animated.timing(fadeAnim, { toValue: 1, duration: 600, useNativeDriver: true }).start();
    Animated.loop(
      Animated.sequence([
        Animated.timing(bounceAnim, { toValue: -8, duration: 1000, useNativeDriver: true }),
        Animated.timing(bounceAnim, { toValue: 0, duration: 1000, useNativeDriver: true }),
      ])
    ).start();
  }, []);

  const loadSettings = async () => {
    try {
      const savedAgeTier = await storage.getItem('ageTier');
      const savedChildId = await storage.getItem('childId');
      if (savedAgeTier) setAgeTier(savedAgeTier);
      if (savedChildId) setChildId(savedChildId);
    } catch (error) {
      console.log('Settings load error:', error);
    }
  };

  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;

    const userMessage: Message = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: text.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      const response = await fetch(`${BACKEND_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          child_id: childId,
          message: text.trim(),
          age_tier: ageTier,
          include_audio: true,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setSessionId(data.session_id);

        const assistantMessage: Message = {
          id: `msg_${Date.now()}_assistant`,
          role: 'assistant',
          content: data.response,
          audioUrl: data.audio_url,
          bibleVerses: data.bible_verses,
          fromKnowledgeBase: data.from_knowledge_base,
          timestamp: new Date(),
        };

        setMessages(prev => [...prev, assistantMessage]);

        // If audio_url came with the response (cached KB), play immediately
        if (data.audio_url) {
          speakText(data.response, data.audio_url);
        } else {
          // Audio is being generated in background - fetch it separately
          fetchAndPlayAudio(data.response, data.session_id, assistantMessage.id);
        }
      }
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        id: `msg_${Date.now()}_error`,
        role: 'assistant',
        content: "Oops! Let me try again. Can you ask me once more? 💙",
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      scrollViewRef.current?.scrollToEnd({ animated: true });
    }
  };

  // Fetch audio separately when text returns without audio (background TTS)
  const fetchAndPlayAudio = async (text: string, sid: string, messageId: string) => {
    // Try the /api/tts endpoint to generate audio
    try {
      const ttsRes = await fetch(`${BACKEND_URL}/api/tts?text=${encodeURIComponent(text)}`, { method: 'POST' });
      if (ttsRes.ok) {
        const ttsData = await ttsRes.json();
        if (ttsData.audio_url) {
          // Update the message with the audio URL
          setMessages(prev => prev.map(m => 
            m.id === messageId ? { ...m, audioUrl: ttsData.audio_url } : m
          ));
          speakText(text, ttsData.audio_url);
          return;
        }
      }
    } catch (e) {
      console.log('fetchAndPlayAudio error:', e);
    }
    // If TTS fetch fails, use device speech
    speakText(text);
  };


  // Audio player ref for ElevenLabs audio
  const soundRef = useRef<Audio.Sound | null>(null);
  const webAudioRef = useRef<HTMLAudioElement | null>(null);

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (soundRef.current) {
        soundRef.current.unloadAsync();
      }
      if (Platform.OS === 'web' && webAudioRef.current) {
        webAudioRef.current.pause();
        webAudioRef.current = null;
      }
    };
  }, []);

  // Build full audio URL from relative path
  const getFullAudioUrl = (audioPath: string) => {
    if (audioPath.startsWith('http')) return audioPath;
    return `${BACKEND_URL}${audioPath}`;
  };

  const speakText = async (text: string, audioUrl?: string) => {
    try {
      setIsPlaying(true);

      // Step 1: Try playing ElevenLabs audio if we have a URL
      if (audioUrl) {
        const fullUrl = getFullAudioUrl(audioUrl);
        console.log('Playing audio from:', fullUrl);
        const played = await playAudio(fullUrl);
        if (played) return;
      }

      // Step 2: Try fetching TTS from backend
      try {
        const ttsRes = await fetch(`${BACKEND_URL}/api/tts?text=${encodeURIComponent(text)}`, { method: 'POST' });
        if (ttsRes.ok) {
          const ttsData = await ttsRes.json();
          if (ttsData.audio_url) {
            const fullUrl = getFullAudioUrl(ttsData.audio_url);
            console.log('Playing TTS audio from:', fullUrl);
            const played = await playAudio(fullUrl);
            if (played) return;
          }
        }
      } catch (e) {
        console.log('TTS fetch error:', e);
      }

      // Step 3: Last resort - device speech synthesis
      console.log('Falling back to device speech');
      if (Platform.OS === 'web') {
        if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
          window.speechSynthesis.cancel();
          const utterance = new SpeechSynthesisUtterance(text);
          utterance.lang = 'en-US';
          utterance.rate = 0.9;
          utterance.pitch = 1.1;
          utterance.onend = () => setIsPlaying(false);
          utterance.onerror = () => setIsPlaying(false);
          window.speechSynthesis.speak(utterance);
        } else {
          setIsPlaying(false);
        }
      } else {
        Speech.speak(text, {
          language: 'en',
          pitch: 1.1,
          rate: 0.9,
          onDone: () => setIsPlaying(false),
          onError: () => setIsPlaying(false),
        });
      }
    } catch (err) {
      console.log('speakText error:', err);
      setIsPlaying(false);
    }
  };

  const playAudio = async (url: string): Promise<boolean> => {
    try {
      if (Platform.OS === 'web') {
        // Web: HTML5 Audio
        return new Promise((resolve) => {
          if (webAudioRef.current) {
            webAudioRef.current.pause();
          }
          const audio = new window.Audio(url);
          webAudioRef.current = audio;
          audio.onended = () => {
            setIsPlaying(false);
            resolve(true);
          };
          audio.onerror = () => {
            console.log('Web audio error');
            setIsPlaying(false);
            resolve(false);
          };
          audio.play().catch((e) => {
            console.log('Web audio play failed:', e);
            setIsPlaying(false);
            resolve(false);
          });
        });
      } else {
        // Native: expo-av with proper HTTP URL
        if (soundRef.current) {
          await soundRef.current.unloadAsync();
        }

        await Audio.setAudioModeAsync({
          allowsRecordingIOS: false,
          playsInSilentModeIOS: true,
          staysActiveInBackground: false,
        });

        console.log('Loading native audio:', url);
        const { sound } = await Audio.Sound.createAsync(
          { uri: url },
          { shouldPlay: true, volume: 1.0 }
        );
        soundRef.current = sound;

        sound.setOnPlaybackStatusUpdate((status) => {
          if (status.isLoaded && status.didJustFinish) {
            setIsPlaying(false);
            sound.unloadAsync();
          }
        });
        return true;
      }
    } catch (e) {
      console.log('playAudio error:', e);
      setIsPlaying(false);
      return false;
    }
  };

  const stopAudio = async () => {
    if (Platform.OS === 'web') {
      if (webAudioRef.current) {
        webAudioRef.current.pause();
        webAudioRef.current = null;
      }
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    } else {
      if (soundRef.current) {
        await soundRef.current.stopAsync();
        await soundRef.current.unloadAsync();
        soundRef.current = null;
      }
      Speech.stop();
    }
    setIsPlaying(false);
  };

  const recordingRef = useRef<Audio.Recording | null>(null);
  const mediaRecorderRef = useRef<any>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const toggleRecording = async () => {
    if (isRecording) {
      await stopRecording();
    } else {
      await startRecording();
    }
  };

  const startRecording = async () => {
    try {
      setIsRecording(true);
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.3, duration: 400, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 400, useNativeDriver: true }),
        ])
      ).start();

      if (Platform.OS === 'web') {
        // Web: use MediaRecorder API
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        audioChunksRef.current = [];
        mediaRecorder.ondataavailable = (e: any) => {
          if (e.data.size > 0) audioChunksRef.current.push(e.data);
        };
        mediaRecorder.start();
        mediaRecorderRef.current = mediaRecorder;
      } else {
        // Native: use expo-av Recording
        const permission = await Audio.requestPermissionsAsync();
        if (!permission.granted) {
          setIsRecording(false);
          pulseAnim.stopAnimation();
          pulseAnim.setValue(1);
          return;
        }
        await Audio.setAudioModeAsync({
          allowsRecordingIOS: true,
          playsInSilentModeIOS: true,
        });
        const { recording } = await Audio.Recording.createAsync(
          Audio.RecordingOptionsPresets.HIGH_QUALITY
        );
        recordingRef.current = recording;
      }
    } catch (e) {
      console.log('Start recording error:', e);
      setIsRecording(false);
      pulseAnim.stopAnimation();
      pulseAnim.setValue(1);
    }
  };

  const stopRecording = async () => {
    setIsRecording(false);
    pulseAnim.stopAnimation();
    pulseAnim.setValue(1);
    setIsLoading(true);

    try {
      let audioBlob: Blob | null = null;
      let audioUri: string | null = null;

      if (Platform.OS === 'web') {
        // Web: stop MediaRecorder and get blob
        const mediaRecorder = mediaRecorderRef.current;
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
          audioBlob = await new Promise<Blob>((resolve) => {
            mediaRecorder.onstop = () => {
              const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
              resolve(blob);
            };
            mediaRecorder.stop();
            // Stop all tracks to release mic
            mediaRecorder.stream.getTracks().forEach((t: any) => t.stop());
          });
        }
      } else {
        // Native: stop expo-av recording
        const rec = recordingRef.current;
        if (rec) {
          await rec.stopAndUnloadAsync();
          audioUri = rec.getURI();
          recordingRef.current = null;
          await Audio.setAudioModeAsync({ allowsRecordingIOS: false });
        }
      }

      // Send to backend for transcription
      const formData = new FormData();
      if (Platform.OS === 'web' && audioBlob) {
        formData.append('file', audioBlob, 'recording.webm');
      } else if (audioUri) {
        const fileObj = { uri: audioUri, type: 'audio/m4a', name: 'recording.m4a' } as any;
        formData.append('file', fileObj);
      } else {
        setIsLoading(false);
        return;
      }

      const res = await fetch(`${BACKEND_URL}/api/voice/transcribe`, {
        method: 'POST',
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        if (data.transcript && data.transcript.trim()) {
          // Use the transcribed text as a message
          sendMessage(data.transcript.trim());
          return; // sendMessage handles setIsLoading
        } else {
          console.log('Empty transcript');
        }
      }
    } catch (e) {
      console.log('Stop recording / transcribe error:', e);
    }
    setIsLoading(false);
  };

  const currentTier = AGE_TIERS.find(t => t.value === ageTier) || AGE_TIERS[1];

  const renderMessage = (message: Message) => {
    const isUser = message.role === 'user';
    return (
      <Animated.View
        key={message.id}
        style={[styles.messageBubble, isUser ? styles.userBubble : styles.assistantBubble]}
      >
        {!isUser && (
          <LinearGradient colors={['#667eea', '#764ba2']} style={styles.avatarGradient}>
            <Text style={styles.avatarEmoji}>📖</Text>
          </LinearGradient>
        )}
        <View style={[styles.messageContent, isUser ? styles.userContent : styles.assistantContent]}>
          {isUser ? (
            <LinearGradient colors={['#FF6B6B', '#FF8E53']} style={styles.userMessageGradient}>
              <Text style={styles.userText}>{message.content}</Text>
            </LinearGradient>
          ) : (
            <>
              <Text style={styles.assistantText}>{message.content}</Text>
              {message.bibleVerses && message.bibleVerses.length > 0 && (
                <View style={styles.versesContainer}>
                  {message.bibleVerses.map((verse, i) => (
                    <View key={i} style={styles.verseChip}>
                      <Ionicons name="book" size={12} color="#6C5CE7" />
                      <Text style={styles.verseText}>{verse}</Text>
                    </View>
                  ))}
                </View>
              )}
              {message.fromKnowledgeBase && (
                <View style={styles.instantBadge}>
                  <Ionicons name="flash" size={14} color="#FFD93D" />
                  <Text style={styles.instantText}>Instant Answer</Text>
                </View>
              )}
              <TouchableOpacity style={styles.listenButton} onPress={() => isPlaying ? stopAudio() : speakText(message.content, message.audioUrl)}>
                <Ionicons name={isPlaying ? 'stop-circle' : 'play-circle'} size={26} color="#4ECDC4" />
                <Text style={styles.listenText}>{isPlaying ? 'Stop' : 'Listen'}</Text>
              </TouchableOpacity>
            </>
          )}
        </View>
      </Animated.View>
    );
  };

  const renderWelcome = () => (
    <Animated.View style={[styles.welcomeContainer, { opacity: fadeAnim }]}>
      <Animated.View style={[styles.welcomeLogo, { transform: [{ translateY: bounceAnim }] }]}>
        <LinearGradient colors={['#667eea', '#764ba2']} style={styles.welcomeLogoGradient}>
          <Text style={styles.welcomeEmoji}>📖</Text>
        </LinearGradient>
        <Text style={styles.welcomeTitle}>Bible Buddy</Text>
        <Text style={styles.welcomeSubtitle}>Ask me anything about God, Jesus, or the Bible!</Text>
      </Animated.View>

      <View style={styles.suggestionsContainer}>
        <Text style={styles.suggestionsTitle}>✨ Try asking:</Text>
        {[
          { text: 'Who made the world?', color: '#FF6B6B', icon: '🌍' },
          { text: 'Tell me about Jesus', color: '#4ECDC4', icon: '✝️' },
          { text: 'How can I pray?', color: '#FFD93D', icon: '🙏' },
          { text: 'Why does God love me?', color: '#6C5CE7', icon: '❤️' },
        ].map((suggestion, i) => (
          <TouchableOpacity
            key={i}
            style={[styles.suggestionCard, { borderLeftColor: suggestion.color }]}
            onPress={() => sendMessage(suggestion.text)}
            activeOpacity={0.7}
          >
            <Text style={styles.suggestionIcon}>{suggestion.icon}</Text>
            <Text style={styles.suggestionText}>{suggestion.text}</Text>
            <View style={[styles.suggestionArrow, { backgroundColor: suggestion.color }]}>
              <Ionicons name="arrow-forward" size={16} color="#fff" />
            </View>
          </TouchableOpacity>
        ))}
      </View>
    </Animated.View>
  );

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      {/* Header */}
      <LinearGradient colors={['#667eea', '#764ba2']} style={styles.header}>
        <SafeAreaView edges={['top']} style={styles.headerContent}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color="#fff" />
          </TouchableOpacity>
          <View style={styles.headerCenter}>
            <Text style={styles.headerTitle}>Bible Buddy</Text>
            <TouchableOpacity onPress={() => setShowSettings(!showSettings)} style={styles.ageBadge}>
              <Text style={styles.ageBadgeEmoji}>{currentTier.emoji}</Text>
              <Text style={styles.ageBadgeText}>{currentTier.label} yrs</Text>
            </TouchableOpacity>
          </View>
          <TouchableOpacity onPress={() => setShowSettings(!showSettings)} style={styles.settingsButton}>
            <Ionicons name="settings" size={24} color="#fff" />
          </TouchableOpacity>
        </SafeAreaView>
      </LinearGradient>

      {/* Settings Panel */}
      {showSettings && (
        <Animated.View style={styles.settingsPanel}>
          <Text style={styles.settingsLabel}>🎂 Select Age Group:</Text>
          <View style={styles.ageGrid}>
            {AGE_TIERS.map((tier) => (
              <TouchableOpacity
                key={tier.value}
                style={[
                  styles.ageButton,
                  ageTier === tier.value && { backgroundColor: tier.color },
                ]}
                onPress={() => { setAgeTier(tier.value); storage.setItem('ageTier', tier.value); }}
              >
                <Text style={styles.ageButtonEmoji}>{tier.emoji}</Text>
                <Text style={[styles.ageButtonText, ageTier === tier.value && { color: '#fff' }]}>
                  {tier.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
          <TouchableOpacity
            style={styles.newChatButton}
            onPress={() => { setMessages([]); setSessionId(null); setShowSettings(false); }}
          >
            <LinearGradient colors={['#FF6B6B', '#FF8E53']} style={styles.newChatGradient}>
              <Ionicons name="refresh" size={20} color="#fff" />
              <Text style={styles.newChatText}>Start New Chat</Text>
            </LinearGradient>
          </TouchableOpacity>
        </Animated.View>
      )}

      {/* Chat Area */}
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.chatArea}>
        <ScrollView
          ref={scrollViewRef}
          style={styles.messagesScroll}
          contentContainerStyle={styles.messagesContent}
          onContentSizeChange={() => scrollViewRef.current?.scrollToEnd({ animated: true })}
        >
          {messages.length === 0 ? renderWelcome() : (
            <>
              {messages.map(renderMessage)}
              {isLoading && (
                <View style={styles.typingContainer}>
                  <LinearGradient colors={['#667eea', '#764ba2']} style={styles.typingAvatar}>
                    <Text style={{ fontSize: 16 }}>📖</Text>
                  </LinearGradient>
                  <View style={styles.typingBubble}>
                    <ActivityIndicator size="small" color="#667eea" />
                    <Text style={styles.typingText}>Thinking...</Text>
                  </View>
                </View>
              )}
            </>
          )}
        </ScrollView>

        {/* Input Area */}
        <View style={styles.inputContainer}>
          <View style={styles.inputWrapper}>
            <TextInput
              style={styles.textInput}
              value={inputText}
              onChangeText={setInputText}
              placeholder="Ask me about the Bible..."
              placeholderTextColor="#999"
              multiline
              maxLength={500}
            />
            <Animated.View style={{ transform: [{ scale: pulseAnim }] }}>
              <TouchableOpacity
                style={[styles.micButton, isRecording && styles.micButtonActive]}
                onPress={toggleRecording}
                data-testid="mic-button"
              >
                <Ionicons name={isRecording ? 'stop' : 'mic'} size={22} color={isRecording ? '#fff' : '#6C5CE7'} />
              </TouchableOpacity>
            </Animated.View>
          </View>
          <TouchableOpacity
            style={[styles.sendButton, (!inputText.trim() || isLoading) && styles.sendButtonDisabled]}
            onPress={() => sendMessage(inputText)}
            disabled={!inputText.trim() || isLoading}
          >
            <LinearGradient
              colors={inputText.trim() && !isLoading ? ['#FF6B6B', '#FF8E53'] : ['#DDD', '#CCC']}
              style={styles.sendGradient}
            >
              <Ionicons name="send" size={22} color="#fff" />
            </LinearGradient>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>

      {/* Playing Indicator */}
      {isPlaying && (
        <View style={styles.playingBar}>
          <Ionicons name="volume-high" size={20} color="#4ECDC4" />
          <Text style={styles.playingText}>🎵 Bible Buddy is speaking...</Text>
          <TouchableOpacity onPress={stopAudio}>
            <Ionicons name="close-circle" size={24} color="#FF6B6B" />
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8F9FF' },
  header: { paddingBottom: 16 },
  headerContent: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingTop: 8 },
  backButton: { padding: 8 },
  headerCenter: { alignItems: 'center' },
  headerTitle: { fontSize: 20, fontWeight: '800', color: '#fff' },
  ageBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.2)', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12, marginTop: 4 },
  ageBadgeEmoji: { fontSize: 14, marginRight: 4 },
  ageBadgeText: { fontSize: 12, color: '#fff', fontWeight: '600' },
  settingsButton: { padding: 8 },
  settingsPanel: { backgroundColor: '#fff', padding: 20, borderBottomLeftRadius: 24, borderBottomRightRadius: 24, shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.1, shadowRadius: 12, elevation: 8 },
  settingsLabel: { fontSize: 16, fontWeight: '700', color: '#2D3436', marginBottom: 12 },
  ageGrid: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 16 },
  ageButton: { flex: 1, alignItems: 'center', paddingVertical: 12, marginHorizontal: 4, borderRadius: 16, backgroundColor: '#F8F9FF' },
  ageButtonEmoji: { fontSize: 24, marginBottom: 4 },
  ageButtonText: { fontSize: 13, fontWeight: '600', color: '#636E72' },
  newChatButton: { borderRadius: 14, overflow: 'hidden' },
  newChatGradient: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 14, gap: 8 },
  newChatText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  chatArea: { flex: 1 },
  messagesScroll: { flex: 1 },
  messagesContent: { padding: 16, paddingBottom: 20 },
  welcomeContainer: { alignItems: 'center', paddingVertical: 20 },
  welcomeLogo: { alignItems: 'center', marginBottom: 24 },
  welcomeLogoGradient: { width: 80, height: 80, borderRadius: 40, alignItems: 'center', justifyContent: 'center', marginBottom: 12 },
  welcomeEmoji: { fontSize: 40 },
  welcomeTitle: { fontSize: 28, fontWeight: '800', color: '#2D3436' },
  welcomeSubtitle: { fontSize: 15, color: '#636E72', marginTop: 6, textAlign: 'center' },
  suggestionsContainer: { width: '100%' },
  suggestionsTitle: { fontSize: 16, fontWeight: '700', color: '#2D3436', marginBottom: 12, textAlign: 'center' },
  suggestionCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', padding: 16, borderRadius: 16, marginBottom: 10, borderLeftWidth: 4, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.06, shadowRadius: 8, elevation: 3 },
  suggestionIcon: { fontSize: 24, marginRight: 12 },
  suggestionText: { flex: 1, fontSize: 15, fontWeight: '600', color: '#2D3436' },
  suggestionArrow: { width: 32, height: 32, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  messageBubble: { flexDirection: 'row', marginBottom: 16, maxWidth: '88%' },
  userBubble: { alignSelf: 'flex-end', flexDirection: 'row-reverse' },
  assistantBubble: { alignSelf: 'flex-start' },
  avatarGradient: { width: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center', marginRight: 10 },
  avatarEmoji: { fontSize: 18 },
  messageContent: { maxWidth: width * 0.72 },
  userContent: { borderRadius: 20, overflow: 'hidden' },
  userMessageGradient: { padding: 14, borderRadius: 20, borderBottomRightRadius: 6 },
  userText: { fontSize: 15, lineHeight: 22, color: '#fff', fontWeight: '500' },
  assistantContent: { backgroundColor: '#fff', borderRadius: 20, borderBottomLeftRadius: 6, padding: 14, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.06, shadowRadius: 8, elevation: 3 },
  assistantText: { fontSize: 15, lineHeight: 22, color: '#2D3436' },
  versesContainer: { flexDirection: 'row', flexWrap: 'wrap', marginTop: 10, gap: 6 },
  verseChip: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#EDE9FE', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 12, gap: 4 },
  verseText: { fontSize: 12, fontWeight: '600', color: '#6C5CE7' },
  instantBadge: { flexDirection: 'row', alignItems: 'center', marginTop: 10, gap: 4 },
  instantText: { fontSize: 12, fontWeight: '600', color: '#FFD93D' },
  listenButton: { flexDirection: 'row', alignItems: 'center', marginTop: 10, paddingTop: 10, borderTopWidth: 1, borderTopColor: '#F0F0F0', gap: 6 },
  listenText: { fontSize: 14, fontWeight: '600', color: '#4ECDC4' },
  typingContainer: { flexDirection: 'row', alignItems: 'center' },
  typingAvatar: { width: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center', marginRight: 10 },
  typingBubble: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', padding: 12, borderRadius: 18, gap: 8 },
  typingText: { fontSize: 14, color: '#636E72' },
  inputContainer: { flexDirection: 'row', alignItems: 'flex-end', padding: 16, backgroundColor: '#fff', borderTopWidth: 1, borderTopColor: '#F0F0F0' },
  inputWrapper: { flex: 1, flexDirection: 'row', alignItems: 'flex-end', backgroundColor: '#F8F9FF', borderRadius: 24, paddingHorizontal: 16, paddingVertical: 8, marginRight: 10 },
  textInput: { flex: 1, fontSize: 15, color: '#2D3436', maxHeight: 100, paddingVertical: 8 },
  micButton: { width: 40, height: 40, borderRadius: 20, backgroundColor: '#EDE9FE', alignItems: 'center', justifyContent: 'center', marginLeft: 8 },
  micButtonActive: { backgroundColor: '#FF6B6B' },
  sendButton: { borderRadius: 24, overflow: 'hidden' },
  sendButtonDisabled: { opacity: 0.6 },
  sendGradient: { width: 50, height: 50, alignItems: 'center', justifyContent: 'center' },
  playingBar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#E0F7F5', paddingVertical: 10, paddingHorizontal: 20, gap: 10 },
  playingText: { flex: 1, fontSize: 14, fontWeight: '600', color: '#2D3436' },
});

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
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Audio } from 'expo-av';
import * as Speech from 'expo-speech';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
const { width } = Dimensions.get('window');

// Age tier options
const AGE_TIERS = [
  { value: '4-6', label: '4-6 years', emoji: '🧒' },
  { value: '7-9', label: '7-9 years', emoji: '👧' },
  { value: '10-12', label: '10-12 years', emoji: '🧑' },
  { value: '13-18', label: '13-18 years', emoji: '👨‍🎓' },
];

// Bible translations
const TRANSLATIONS = [
  { value: 'NIV', label: 'NIV' },
  { value: 'KJV', label: 'KJV' },
  { value: 'Good News', label: 'Good News' },
  { value: 'Message', label: 'Message' },
];

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  audioUrl?: string;
  timestamp: Date;
}

export default function BibleBuddyApp() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [userId, setUserId] = useState<string>('');
  const [ageTier, setAgeTier] = useState('7-9');
  const [translation, setTranslation] = useState('NIV');
  const [showSettings, setShowSettings] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentSound, setCurrentSound] = useState<Audio.Sound | null>(null);
  
  const scrollViewRef = useRef<ScrollView>(null);
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const bounceAnim = useRef(new Animated.Value(0)).current;

  // Initialize user on mount
  useEffect(() => {
    initializeUser();
    startBounceAnimation();
    
    return () => {
      if (currentSound) {
        currentSound.unloadAsync();
      }
    };
  }, []);

  const startBounceAnimation = () => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(bounceAnim, {
          toValue: -10,
          duration: 1000,
          useNativeDriver: true,
        }),
        Animated.timing(bounceAnim, {
          toValue: 0,
          duration: 1000,
          useNativeDriver: true,
        }),
      ])
    ).start();
  };

  const startPulseAnimation = () => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.2,
          duration: 500,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 500,
          useNativeDriver: true,
        }),
      ])
    ).start();
  };

  const initializeUser = async () => {
    try {
      // Generate a simple user ID
      const newUserId = `user_${Date.now()}`;
      setUserId(newUserId);
      
      // Create user profile
      const response = await fetch(`${BACKEND_URL}/api/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'Bible Buddy Friend',
          age_tier: ageTier,
          preferred_translation: translation,
        }),
      });
      
      if (response.ok) {
        const user = await response.json();
        setUserId(user.id);
      }
    } catch (error) {
      console.log('User initialization:', error);
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
          user_id: userId,
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
          timestamp: new Date(),
        };

        setMessages(prev => [...prev, assistantMessage]);

        // Auto-play audio response
        if (data.audio_url) {
          playAudio(data.audio_url);
        }
      } else {
        throw new Error('Failed to get response');
      }
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        id: `msg_${Date.now()}_error`,
        role: 'assistant',
        content: "Oops! I'm having a little trouble right now. Can you try asking again? I love talking about the Bible with you! 💙",
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      scrollViewRef.current?.scrollToEnd({ animated: true });
    }
  };

  const playAudio = async (audioUrl: string) => {
    try {
      // Stop any currently playing audio
      if (currentSound) {
        await currentSound.stopAsync();
        await currentSound.unloadAsync();
      }

      setIsPlaying(true);

      // Create and play the audio
      const { sound } = await Audio.Sound.createAsync(
        { uri: audioUrl },
        { shouldPlay: true }
      );

      setCurrentSound(sound);

      sound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded && status.didJustFinish) {
          setIsPlaying(false);
          sound.unloadAsync();
        }
      });
    } catch (error) {
      console.error('Audio playback error:', error);
      setIsPlaying(false);
      // Fallback to device TTS
      Speech.speak(messages[messages.length - 1]?.content || '', {
        language: 'en',
        pitch: 1.1,
        rate: 0.9,
      });
    }
  };

  const stopAudio = async () => {
    if (currentSound) {
      await currentSound.stopAsync();
      setIsPlaying(false);
    }
    Speech.stop();
  };

  const speakText = (text: string) => {
    Speech.speak(text, {
      language: 'en',
      pitch: 1.1,
      rate: 0.9,
    });
  };

  const handleVoiceInput = () => {
    // For now, show a tip - voice recognition would need expo-speech-recognition
    setIsRecording(!isRecording);
    if (!isRecording) {
      startPulseAnimation();
      // Simulate voice recording UI feedback
      setTimeout(() => {
        setIsRecording(false);
        pulseAnim.stopAnimation();
        pulseAnim.setValue(1);
      }, 3000);
    }
  };

  const renderMessage = (message: Message, index: number) => {
    const isUser = message.role === 'user';
    
    return (
      <View
        key={message.id}
        style={[
          styles.messageBubble,
          isUser ? styles.userBubble : styles.assistantBubble,
        ]}
      >
        {!isUser && (
          <View style={styles.avatarContainer}>
            <Text style={styles.avatar}>📖</Text>
          </View>
        )}
        <View style={[
          styles.messageContent,
          isUser ? styles.userContent : styles.assistantContent,
        ]}>
          <Text style={[
            styles.messageText,
            isUser ? styles.userText : styles.assistantText,
          ]}>
            {message.content}
          </Text>
          {!isUser && message.audioUrl && (
            <TouchableOpacity
              style={styles.audioButton}
              onPress={() => isPlaying ? stopAudio() : playAudio(message.audioUrl!)}
            >
              <Ionicons
                name={isPlaying ? 'stop-circle' : 'play-circle'}
                size={28}
                color="#4A90D9"
              />
              <Text style={styles.audioButtonText}>
                {isPlaying ? 'Stop' : 'Listen'}
              </Text>
            </TouchableOpacity>
          )}
        </View>
      </View>
    );
  };

  const renderWelcomeScreen = () => (
    <View style={styles.welcomeContainer}>
      <Animated.View style={[styles.logoContainer, { transform: [{ translateY: bounceAnim }] }]}>
        <Text style={styles.logoEmoji}>📖</Text>
        <Text style={styles.logoText}>Bible Buddy</Text>
      </Animated.View>
      
      <Text style={styles.welcomeText}>
        Hi there, friend! I'm Bible Buddy!{'\n'}
        Ask me anything about God, Jesus, or the Bible!
      </Text>

      <View style={styles.suggestionContainer}>
        <Text style={styles.suggestionTitle}>Try asking me:</Text>
        {[
          "Who made the world?",
          "Tell me about Jesus",
          "How can I pray?",
          "Why does God love me?",
        ].map((suggestion, index) => (
          <TouchableOpacity
            key={index}
            style={styles.suggestionButton}
            onPress={() => sendMessage(suggestion)}
          >
            <Text style={styles.suggestionText}>{suggestion}</Text>
            <Ionicons name="arrow-forward-circle" size={20} color="#4A90D9" />
          </TouchableOpacity>
        ))}
      </View>

      {/* Featured Teachers Section */}
      <View style={styles.teachersSection}>
        <Text style={styles.teachersTitle}>Wisdom from Amazing Teachers</Text>
        <Text style={styles.teachersSubtitle}>
          I also share insights from these inspiring pastors:
        </Text>
        <View style={styles.teachersList}>
          <View style={styles.teacherChip}>
            <Text style={styles.teacherEmoji}>🎤</Text>
            <Text style={styles.teacherName}>Apostle Selman</Text>
          </View>
          <View style={styles.teacherChip}>
            <Text style={styles.teacherEmoji}>💜</Text>
            <Text style={styles.teacherName}>Stephanie Ike</Text>
          </View>
          <View style={styles.teacherChip}>
            <Text style={styles.teacherEmoji}>🔥</Text>
            <Text style={styles.teacherName}>Steven Furtick</Text>
          </View>
          <View style={styles.teacherChip}>
            <Text style={styles.teacherEmoji}>⚔️</Text>
            <Text style={styles.teacherName}>Priscilla Shirer</Text>
          </View>
        </View>
      </View>
    </View>
  );

  const renderSettings = () => (
    <View style={styles.settingsContainer}>
      <View style={styles.settingsHeader}>
        <Text style={styles.settingsTitle}>Settings</Text>
        <TouchableOpacity onPress={() => setShowSettings(false)}>
          <Ionicons name="close-circle" size={32} color="#666" />
        </TouchableOpacity>
      </View>

      <Text style={styles.settingsLabel}>Your Age Group:</Text>
      <View style={styles.optionsRow}>
        {AGE_TIERS.map((tier) => (
          <TouchableOpacity
            key={tier.value}
            style={[
              styles.optionButton,
              ageTier === tier.value && styles.optionButtonActive,
            ]}
            onPress={() => setAgeTier(tier.value)}
          >
            <Text style={styles.optionEmoji}>{tier.emoji}</Text>
            <Text style={[
              styles.optionText,
              ageTier === tier.value && styles.optionTextActive,
            ]}>
              {tier.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={styles.settingsLabel}>Bible Translation:</Text>
      <View style={styles.translationRow}>
        {TRANSLATIONS.map((t) => (
          <TouchableOpacity
            key={t.value}
            style={[
              styles.translationButton,
              translation === t.value && styles.translationButtonActive,
            ]}
            onPress={() => setTranslation(t.value)}
          >
            <Text style={[
              styles.translationText,
              translation === t.value && styles.translationTextActive,
            ]}>
              {t.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <TouchableOpacity
        style={styles.newChatButton}
        onPress={() => {
          setMessages([]);
          setSessionId(null);
          setShowSettings(false);
        }}
      >
        <Ionicons name="refresh" size={20} color="#fff" />
        <Text style={styles.newChatButtonText}>Start New Chat</Text>
      </TouchableOpacity>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Text style={styles.headerEmoji}>📖</Text>
          <View>
            <Text style={styles.headerTitle}>Bible Buddy</Text>
            <Text style={styles.headerSubtitle}>Your friendly Bible friend</Text>
          </View>
        </View>
        <TouchableOpacity
          style={styles.settingsButton}
          onPress={() => setShowSettings(!showSettings)}
        >
          <Ionicons name="settings-outline" size={24} color="#4A90D9" />
        </TouchableOpacity>
      </View>

      {/* Settings Panel */}
      {showSettings && renderSettings()}

      {/* Chat Area */}
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.chatContainer}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 0}
      >
        <ScrollView
          ref={scrollViewRef}
          style={styles.messagesContainer}
          contentContainerStyle={styles.messagesContent}
          showsVerticalScrollIndicator={false}
          onContentSizeChange={() => scrollViewRef.current?.scrollToEnd({ animated: true })}
        >
          {messages.length === 0 ? renderWelcomeScreen() : (
            <>
              {messages.map((msg, index) => renderMessage(msg, index))}
              {isLoading && (
                <View style={styles.loadingContainer}>
                  <View style={styles.typingIndicator}>
                    <Text style={styles.typingEmoji}>📖</Text>
                    <View style={styles.typingDots}>
                      <ActivityIndicator size="small" color="#4A90D9" />
                      <Text style={styles.typingText}>Bible Buddy is thinking...</Text>
                    </View>
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
              onSubmitEditing={() => sendMessage(inputText)}
            />
            
            {/* Voice Button */}
            <Animated.View style={{ transform: [{ scale: pulseAnim }] }}>
              <TouchableOpacity
                style={[styles.voiceButton, isRecording && styles.voiceButtonActive]}
                onPress={handleVoiceInput}
              >
                <Ionicons
                  name={isRecording ? 'mic' : 'mic-outline'}
                  size={24}
                  color={isRecording ? '#fff' : '#4A90D9'}
                />
              </TouchableOpacity>
            </Animated.View>
          </View>
          
          {/* Send Button */}
          <TouchableOpacity
            style={[styles.sendButton, (!inputText.trim() || isLoading) && styles.sendButtonDisabled]}
            onPress={() => sendMessage(inputText)}
            disabled={!inputText.trim() || isLoading}
          >
            <Ionicons name="send" size={20} color="#fff" />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>

      {/* Playing Indicator */}
      {isPlaying && (
        <View style={styles.playingIndicator}>
          <Ionicons name="volume-high" size={20} color="#4A90D9" />
          <Text style={styles.playingText}>Bible Buddy is speaking...</Text>
          <TouchableOpacity onPress={stopAudio}>
            <Ionicons name="close-circle" size={24} color="#666" />
          </TouchableOpacity>
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F0F7FF',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#E8F0FE',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  headerEmoji: {
    fontSize: 36,
    marginRight: 12,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#2C3E50',
  },
  headerSubtitle: {
    fontSize: 12,
    color: '#7F8C8D',
    marginTop: 2,
  },
  settingsButton: {
    padding: 8,
  },
  chatContainer: {
    flex: 1,
  },
  messagesContainer: {
    flex: 1,
  },
  messagesContent: {
    padding: 16,
    paddingBottom: 20,
  },
  welcomeContainer: {
    alignItems: 'center',
    paddingVertical: 30,
  },
  logoContainer: {
    alignItems: 'center',
    marginBottom: 20,
  },
  logoEmoji: {
    fontSize: 80,
    marginBottom: 10,
  },
  logoText: {
    fontSize: 32,
    fontWeight: '700',
    color: '#4A90D9',
  },
  welcomeText: {
    fontSize: 18,
    textAlign: 'center',
    color: '#555',
    lineHeight: 26,
    paddingHorizontal: 20,
    marginBottom: 30,
  },
  suggestionContainer: {
    width: '100%',
    paddingHorizontal: 16,
  },
  suggestionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#666',
    marginBottom: 12,
    textAlign: 'center',
  },
  suggestionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#fff',
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderRadius: 16,
    marginBottom: 10,
    shadowColor: '#4A90D9',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 2,
  },
  suggestionText: {
    fontSize: 16,
    color: '#333',
    flex: 1,
  },
  messageBubble: {
    flexDirection: 'row',
    marginBottom: 16,
    maxWidth: '85%',
  },
  userBubble: {
    alignSelf: 'flex-end',
    flexDirection: 'row-reverse',
  },
  assistantBubble: {
    alignSelf: 'flex-start',
  },
  avatarContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#E8F0FE',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 8,
  },
  avatar: {
    fontSize: 24,
  },
  messageContent: {
    borderRadius: 20,
    padding: 14,
    maxWidth: width * 0.7,
  },
  userContent: {
    backgroundColor: '#4A90D9',
    borderBottomRightRadius: 4,
  },
  assistantContent: {
    backgroundColor: '#fff',
    borderBottomLeftRadius: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 1,
  },
  messageText: {
    fontSize: 16,
    lineHeight: 22,
  },
  userText: {
    color: '#fff',
  },
  assistantText: {
    color: '#333',
  },
  audioButton: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 10,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: '#E8F0FE',
  },
  audioButtonText: {
    marginLeft: 6,
    fontSize: 14,
    color: '#4A90D9',
    fontWeight: '500',
  },
  loadingContainer: {
    alignItems: 'flex-start',
    marginTop: 8,
  },
  typingIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 1,
  },
  typingEmoji: {
    fontSize: 24,
    marginRight: 10,
  },
  typingDots: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  typingText: {
    marginLeft: 8,
    fontSize: 14,
    color: '#666',
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#E8F0FE',
  },
  inputWrapper: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'flex-end',
    backgroundColor: '#F8FAFC',
    borderRadius: 24,
    paddingHorizontal: 16,
    paddingVertical: 8,
    marginRight: 10,
    minHeight: 48,
  },
  textInput: {
    flex: 1,
    fontSize: 16,
    color: '#333',
    maxHeight: 100,
    paddingVertical: 8,
  },
  voiceButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#E8F0FE',
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 8,
  },
  voiceButtonActive: {
    backgroundColor: '#4A90D9',
  },
  sendButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#4A90D9',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#4A90D9',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  sendButtonDisabled: {
    backgroundColor: '#B8D4F0',
    shadowOpacity: 0,
  },
  settingsContainer: {
    backgroundColor: '#fff',
    paddingHorizontal: 20,
    paddingVertical: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#E8F0FE',
  },
  settingsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  settingsTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#2C3E50',
  },
  settingsLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
    marginBottom: 10,
    marginTop: 10,
  },
  optionsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  optionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 12,
    backgroundColor: '#F0F7FF',
    borderWidth: 2,
    borderColor: 'transparent',
  },
  optionButtonActive: {
    borderColor: '#4A90D9',
    backgroundColor: '#E8F0FE',
  },
  optionEmoji: {
    fontSize: 18,
    marginRight: 6,
  },
  optionText: {
    fontSize: 13,
    color: '#666',
  },
  optionTextActive: {
    color: '#4A90D9',
    fontWeight: '600',
  },
  translationRow: {
    flexDirection: 'row',
    gap: 8,
  },
  translationButton: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    backgroundColor: '#F0F7FF',
    borderWidth: 2,
    borderColor: 'transparent',
  },
  translationButtonActive: {
    borderColor: '#4A90D9',
    backgroundColor: '#E8F0FE',
  },
  translationText: {
    fontSize: 14,
    color: '#666',
  },
  translationTextActive: {
    color: '#4A90D9',
    fontWeight: '600',
  },
  newChatButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4A90D9',
    paddingVertical: 14,
    borderRadius: 12,
    marginTop: 20,
  },
  newChatButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  playingIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#E8F0FE',
    paddingVertical: 10,
    paddingHorizontal: 20,
    gap: 10,
  },
  playingText: {
    fontSize: 14,
    color: '#4A90D9',
    flex: 1,
  },
  // Featured Teachers Styles
  teachersSection: {
    marginTop: 30,
    paddingHorizontal: 16,
    width: '100%',
  },
  teachersTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#4A90D9',
    textAlign: 'center',
    marginBottom: 6,
  },
  teachersSubtitle: {
    fontSize: 13,
    color: '#888',
    textAlign: 'center',
    marginBottom: 14,
  },
  teachersList: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 8,
  },
  teacherChip: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 20,
    shadowColor: '#4A90D9',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 1,
  },
  teacherEmoji: {
    fontSize: 14,
    marginRight: 6,
  },
  teacherName: {
    fontSize: 12,
    color: '#555',
    fontWeight: '500',
  },
});

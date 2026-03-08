import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface BibleVerseCardProps {
  verse: string;
}

export function BibleVerseCard({ verse }: BibleVerseCardProps) {
  return (
    <View style={styles.container}>
      <View style={styles.iconContainer}>
        <Ionicons name="book" size={16} color="#4A90D9" />
      </View>
      <Text style={styles.verseText}>{verse}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F0F7FF',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 16,
    marginRight: 8,
    marginTop: 8,
  },
  iconContainer: {
    marginRight: 6,
  },
  verseText: {
    fontSize: 12,
    color: '#4A90D9',
    fontWeight: '500',
  },
});

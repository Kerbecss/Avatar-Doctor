using System;
using System.Collections.Generic;
using NUnit.Framework;
using Teyocesu.AvatarDoctor.Editor.Discovery;
using UnityEngine;

namespace Teyocesu.AvatarDoctor.Editor.Tests
{
    internal sealed class AvatarDiscoveryResultTests
    {
        private readonly List<GameObject> objects = new List<GameObject>();

        [TearDown]
        public void TearDown()
        {
            foreach (GameObject gameObject in objects)
            {
                if (gameObject != null)
                {
                    UnityEngine.Object.DestroyImmediate(gameObject);
                }
            }

            objects.Clear();
        }

        [Test]
        public void Constructor_WithNoCandidates_DerivesNoneState()
        {
            AvatarDiscoveryResult result = new AvatarDiscoveryResult(
                Array.Empty<AvatarDiscoveryCandidate>());

            Assert.That(result.Candidates, Is.Empty);
            Assert.That(result.CountState, Is.EqualTo(AvatarDiscoveryState.None));
        }

        [Test]
        public void Constructor_WithOneCandidate_DerivesSingleState()
        {
            AvatarDiscoveryResult result = new AvatarDiscoveryResult(
                new[] { CreateCandidate("Avatar", 0) });

            Assert.That(result.Candidates, Has.Count.EqualTo(1));
            Assert.That(result.CountState, Is.EqualTo(AvatarDiscoveryState.Single));
        }

        [Test]
        public void Constructor_WithMultipleCandidates_DerivesMultipleState()
        {
            AvatarDiscoveryResult result = new AvatarDiscoveryResult(
                new[]
                {
                    CreateCandidate("Avatar A", 0),
                    CreateCandidate("Avatar B", 1),
                });

            Assert.That(result.Candidates, Has.Count.EqualTo(2));
            Assert.That(
                result.CountState,
                Is.EqualTo(AvatarDiscoveryState.Multiple));
        }

        [Test]
        public void Constructor_CopiesAndExposesReadOnlyCandidateCollection()
        {
            AvatarDiscoveryCandidate first = CreateCandidate("Avatar A", 0);
            AvatarDiscoveryCandidate second = CreateCandidate("Avatar B", 1);
            List<AvatarDiscoveryCandidate> source =
                new List<AvatarDiscoveryCandidate> { first };

            AvatarDiscoveryResult result = new AvatarDiscoveryResult(source);
            source.Add(second);

            Assert.That(result.Candidates, Has.Count.EqualTo(1));
            IList<AvatarDiscoveryCandidate> list =
                result.Candidates as IList<AvatarDiscoveryCandidate>;
            Assert.That(list, Is.Not.Null);
            Assert.That(list.IsReadOnly, Is.True);
            Assert.Throws<NotSupportedException>(() => list.Add(second));
        }

        private AvatarDiscoveryCandidate CreateCandidate(
            string name,
            int siblingIndex)
        {
            GameObject gameObject = new GameObject(name);
            objects.Add(gameObject);
            return new AvatarDiscoveryCandidate(
                gameObject,
                gameObject,
                0,
                name,
                "Assets/Test.unity",
                name + " [" + siblingIndex + "]",
                true,
                "Assets/Test.unity",
                0,
                "Test",
                new[] { siblingIndex },
                gameObject.GetInstanceID(),
                1);
        }
    }
}

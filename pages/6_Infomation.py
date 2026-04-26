import streamlit as st
import pandas as pd

st.set_page_config(page_title="Information", layout="wide")

st.title("Information")

# Rules and Guidelines section
with st.expander("Rules and Guidelines"):

    # Subsection: Match Format
    st.subheader("Match Format")
    st.markdown(
        """
        1. Matches are best of 2 x 6 sets, with a 7- or 10-point match tiebreak in lieu of a third set. \n
        2. If court window is short 2 x 4 with no ads are accpeted, to be agreed upon by both players before the match. \n
        3. If a match is interrupted, and cannot be rescheduled the players must decide on and report a winner. \n
        4. Players are expected to play their matches within the scheduled match window. Failure to do so results in a default loss. \n
        5. No shows result in a default loss for the player who fails to show up. \n
        """
    )

    # Subsection: Ladder Format
    st.subheader("Ladder Format")
    st.markdown(
        """
        1. Players are sorted into boxes of 5 players based on ELO ratings. \n
        2. Each round lasts 3 weeks, during which time 3 matches must be completed against 3/4 (unique) of the players in the box. \n
        3. After each round, players are promoted or relegated according to the change in ELO ratings. \n
        4. Failure to complete the required matches within the round results in a default loss for each unplayed match. \n
        5. If a player is injured or unable to play a round they can set their status to inactive on the **Home** page under **Update Status**. \n
        6. Players must set themselves as inactive before the start of the round. Failure to do so results in a default loss for each unplayed match. \n
        7. Ranking at the end of season will determine the seeding for the end of season tournament. \n
        """
    )

    # Subsection: Match Reporting
    st.subheader("Match Reporting")
    st.markdown(
        """
        1. Matches are reported by the winner of the match. \n
        2. Match results must be reported within the round window. Failure to report a match results in a default loss for the player who fails to report. \n
        3. Matches are reported on the **Home** page under **Submit Match**. \n
        4. Players are expected to report match results accurately and honestly. \n
        5. Any disputes regarding match results should be reported to the ladder organizers for resolution. \n
        """
    )

    # Subsection: Challenges
    st.subheader("Challenges")
    st.markdown(
        """
        1. Players have one challenge per round. \n
        2. Challenges can only be used on opponenets with higher ELO ratings. \n
        3. Challenges must be initiated within the round window. \n
        4. If a player is challenged more than once in a round, they may choose which challenge to accept, or all. \n
        5. Failure to schedule a challenge match does not result in a default loss. \n
        """
    )

    # Subsection: Player Eligibility
    st.subheader("Player Eligibility")
    st.markdown(
        """
        1. Everyone is welcome to join the ladder, regardless of skill level. \n
        2. We operate on a 2-strike policy. 2 conduct violations results in immediate removal from the ladder. \n
        3. Players are expected to treat each other with respect and sportsmanship. \n
        4. Any disputes or issues should be reported to the ladder organizers for resolution. \n
        """
    )


# Section: ELO System
with st.expander("ELO System"):
    st.markdown(
        """
        The Elo rating is a way of measuring a player's results over the season. Every
        player starts with the same rating, **1500**, and that number moves up or down
        after each completed match.

        When two players play, the system compares their ratings before the match. If a
        higher-rated player beats a lower-rated player, their rating will usually go up
        by a smaller amount because that result was expected. If a lower-rated player
        beats a higher-rated player, they will gain more points because it was a tougher
        result to earn.

        The score of the match also matters. A close win will move the ratings less,
        while a more decisive win will move the ratings more. This helps the rating
        reflect not just who won, but how strongly they performed in that match.

        Elo is updated match by match in the order the matches were played. It is not a
        permanent ranking of ability, but a season-long form rating that rewards winning,
        strong performances, and good results against highly rated opponents.
        
        The main goal of Elo is to help create better skill-based matchups. Over time,
        the ratings give the ladder a clearer picture of which players are getting
        similar results, so players can find competitive matches that feel fair and fun.

        Elo should be treated as a matchmaking tool, not a final statement about a
        player's tennis ability. Form changes, players improve, injuries happen, and
        styles can match up differently. The rating is simply one helpful signal based
        on completed ladder matches.
        """
    )
    st.markdown(
        """
        The system estimates how likely each player is to win based on their ratings:

        `Expected Score = 1 / (1 + 10 ^ ((Opponent Rating - Your Rating) / 400))`

        After the match, your rating is updated like this:

        `New Rating = Old Rating + Match Weight x (Actual Result - Expected Result)`

        In plain language:

        - **Actual Result** is 1 for a win and 0 for a loss.
        - **Expected Result** is higher when you are rated above your opponent and lower
          when you are rated below them.
        - **Match Weight** controls how many points can move. In this ladder, the match
          score also affects the weight, so a decisive win moves ratings more than a
          very close win.
        """
    )


# Section: Contact Information
with st.expander("Contact Information"):
    st.markdown(
        """
        Dovercourt Ladder Organizer: Laurence Braun [laurencewbraun@gmail](mailto:laurencewbraun@gmail.com) \n
        Dovercourt Ladder Website Admin: Karim Sayed [karimelsayed44800@gmail.com](mailto:karimelsayed44800@gmail.com) \n
        Dovercourt Ladder Website Admin: Adam Smith [adam.smith2214@gmail.com](mailto:adam.smith2214@gmail.com)
        """
    )

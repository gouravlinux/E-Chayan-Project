from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from .models import UserProfile, Election, Candidate, Vote, VoterRecord
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone  # Import this to check dates
from django.db.models import Q, Count # Import for complex queries and counting
from django.contrib import messages # To show success/error messages

# --- 1. Home Page ---
# (Added logic for live turnout)
def home_page(request):
    try:
        # Get all users who are verified to vote
        total_voters = UserProfile.objects.filter(is_verified=True).count()
        # Get all records of votes cast in all elections
        total_votes_cast = VoterRecord.objects.count()
        
        if total_voters > 0:
            turnout = (total_votes_cast / (total_voters * Election.objects.count())) * 100 # Simple example
            turnout_percentage = round(turnout, 1)
        else:
            turnout_percentage = 0
    except Exception:
        turnout_percentage = 0

    context = {'turnout_percentage': turnout_percentage}
    return render(request, "votingApp/home.html", context)


# --- 2. Registration Page ---
# (Added error handling and fixed a typo)
def register_page(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        fname = request.POST.get("first_name")
        lname = request.POST.get("last_name")
        age = request.POST.get("age")
        state = request.POST.get("state")
        
        context = {'states': UserProfile.StateChoices.choices}

        # --- ADDED Error Handling ---
        if User.objects.filter(username=username).exists():
            context['error'] = "Username is already taken."
            return render(request, 'votingApp/register.html', context)
        if User.objects.filter(email=email).exists():
            context['error'] = "Email is already registered."
            return render(request, 'votingApp/register.html', context)
        # --- End Error Handling ---

        # Create the User
        new_user = User.objects.create_user(
            username=username, password=password, email=email
        )
        new_user.first_name = fname
        new_user.last_name = lname # <-- FIXED TYPO (was .last)
        new_user.save()

        # Create the UserProfile
        UserProfile.objects.create(user=new_user, age=age, state=state)
        
        messages.success(request, "Registration successful! Please login.")
        return redirect('login')

    # if GET request, just show the page
    # pass the state choices from your model to the template
    context = {'states': UserProfile.StateChoices.choices}
    return render(request, 'votingApp/register.html', context)


# --- 3. Login Page ---
# (Added support for messages)
def login_page(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            # Using context error for your template's design
            return render(request, 'votingApp/login.html', {"error": "Invalid credentials"})
    
    return render(request, 'votingApp/login.html')


# --- 4. Logout Page ---
def logout_page(request):
    logout(request)
    return redirect('home')


# --- 5. Dashboard Page ---
# (HEAVILY UPGRADED to show eligible elections)
@login_required
def dashboard_page(request):
    now = timezone.now()
    profile = request.user.userprofile
    
    # 1. Get all active elections
    active_elections = Election.objects.filter(
        start_time__lte=now, 
        end_time__gte=now
    )
    
    # 2. Filter for eligibility (Verified + (National OR correct State))
    eligible_elections_query = active_elections.filter(
        Q(election_type=Election.Electiontype.NATIONAL) | 
        Q(election_type=Election.Electiontype.STATE, state=profile.state)
    )

    # 3. Get list of elections this user has ALREADY voted in
    voted_election_ids = VoterRecord.objects.filter(user=request.user).values_list('election_id', flat=True)

    eligible_elections = []
    
    # 4. Process the list to add the 'user_has_voted' status
    if profile.is_verified: # Only show elections if user is verified
        for election in eligible_elections_query:
            if election.id in voted_election_ids:
                election.user_has_voted = True
            else:
                election.user_has_voted = False
            eligible_elections.append(election)

    context = {
        'user_profile': profile, # This is for the "Your Profile" card
        'eligible_elections': eligible_elections # For the "Available Elections" list
    }
    
    # --- FIXED Template Path ---
    return render(request, 'votingApp/voting_dashboard.html', context)


# --- 6. Results Page ---
# (HEAVILY UPGRADED to calculate and show results)
def results_page(request):
    now = timezone.now()
    elections = Election.objects.all()
    elections_with_results = []

    for election in elections:
        if election.end_time > now:
            # Election is still active
            election.is_active = True
        else:
            # Election has ended, calculate results
            election.is_active = False
            results_dict = {}
            winner = None
            max_votes = -1

            # Get candidates for this election
            candidates = election.candidates.all()
            
            # Count votes for each candidate
            for candidate in candidates:
                vote_count = Vote.objects.filter(candidate=candidate).count()
                results_dict[candidate] = vote_count
                
                if vote_count > max_votes:
                    max_votes = vote_count
                    winner = candidate
            
            # Sort results by vote count (highest first)
            election.results = dict(sorted(results_dict.items(), key=lambda item: item[1], reverse=True))
            election.winner = winner

        elections_with_results.append(election)

    context = {'elections_with_results': elections_with_results}
    return render(request, 'votingApp/results.html', context)


# --- 7. NEW VIEW: Cast Vote Page ---
# (This page shows candidates and handles the vote submission)
@login_required
def vote_page(request, election_slug):
    election = get_object_or_404(Election, slug=election_slug)
    profile = request.user.userprofile
    now = timezone.now()

    # --- Security & Logic Checks ---
    # 1. Is user verified?
    if not profile.is_verified:
        messages.error(request, "You are not verified to vote.")
        return redirect('dashboard')

    # 2. Is election active?
    if not (election.start_time <= now and election.end_time >= now):
        messages.error(request, "This election is not currently active.")
        return redirect('dashboard')
    
    # 3. Is user eligible for this election?
    is_eligible = (
        election.election_type == Election.Electiontype.NATIONAL or
        (election.election_type == Election.Electiontype.STATE and election.state == profile.state)
    )
    if not is_eligible:
        messages.error(request, "You are not eligible for this election.")
        return redirect('dashboard')

    # 4. Has user already voted?
    if VoterRecord.objects.filter(user=request.user, election=election).exists():
        messages.error(request, "You have already voted in this election.")
        return redirect('dashboard')

    # --- Handle the Vote Submission (POST) ---
    if request.method == 'POST':
        # Get the ID of the candidate they selected
        candidate_id = request.POST.get('candidate')
        if not candidate_id:
            # Error: User submitted the form without selecting anyone
            messages.error(request, "Please select a candidate.")
            context = {'election': election}
            return render(request, 'votingApp/vote_page.html', context)
        
        selected_candidate = get_object_or_404(Candidate, id=candidate_id)

        # --- CAST THE VOTE ---
        # 1. Create the anonymous Vote
        Vote.objects.create(candidate=selected_candidate, election=election)
        
        # 2. Create the VoterRecord to prevent double-voting
        VoterRecord.objects.create(user=request.user, election=election)
        
        messages.success(request, f"Your vote for {selected_candidate.name} has been cast!")
        return redirect('dashboard')

    # --- Show the Voting Page (GET) ---
    context = {'election': election} # The template will loop through election.candidates
    return render(request, 'votingApp/vote_page.html', context)

